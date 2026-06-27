"""
Stripe webhook processing for SwarmOS monetization.

This module handles incoming Stripe webhook events, validates signatures,
ensures idempotency, persists project records, triggers the Replicator
engine, and sends delivery emails when appropriate.
"""

import asyncio
import logging
import os
import uuid

import stripe
from fastapi import APIRouter, HTTPException, Request

from agents.outreach.email_engine import EmailTools
from backend.db.linear_engine import get_swarm_db
from backend.replicator import replicator_engine

router = APIRouter(prefix="/api/webhooks", tags=["Monetization"])
logger = logging.getLogger("SwarmWebhooks")

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

# Database instance
DB = get_swarm_db()


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle incoming Stripe webhook events.

    Validates the signature, ensures idempotency, processes checkout
    completion events, triggers Replicator, and sends delivery emails.

    Args:
        request (Request): Raw FastAPI request containing Stripe payload.

    Raises:
        HTTPException: If signature is invalid or processing fails.

    Returns:
        dict: Status response.
    """
    payload = await request.body()

    signature = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")

    if not signature:
        logger.error("Missing Stripe signature header")
        raise HTTPException(status_code=400, detail="Missing signature header")

    # Validate webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.error("Stripe signature verification failed: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Invalid signature",
        ) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error parsing webhook: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Invalid payload",
        ) from exc

    event_id = event.get("id")

    # Idempotency check
    if event_id and DB.is_event_processed(event_id):
        logger.info("Duplicate event received: %s", event_id)
        return {"status": "success", "note": "already_processed"}

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            customer_email = session.get("customer_details", {}).get("email")
            project_id = (
                session.get("metadata", {}).get("project_id") or uuid.uuid4().hex[:8].upper()
            )

            logger.info(
                "PAYMENT RECEIVED from %s. Delivering Box for project %s...",
                customer_email,
                project_id,
            )

            # Persist project record with retry (exponential backoff, max 3 attempts)
            project_created = False
            last_exc = None
            for attempt in range(1, 4):
                try:
                    DB.create_project(
                        project_id,
                        stripe_session=session.get("id"),
                        customer_email=customer_email,
                        product_id=None,
                        price_id=None,
                        metadata=str(session.get("metadata")),
                    )
                    project_created = True
                    break
                except Exception as exc:  # pylint: disable=broad-except
                    last_exc = exc
                    logger.warning(
                        "create_project attempt %d/3 failed for %s: %s",
                        attempt,
                        project_id,
                        exc,
                    )
                    if attempt < 3:
                        await asyncio.sleep(2**attempt)

            if not project_created:
                logger.error(
                    "All retries exhausted for create_project(%s): %s", project_id, last_exc
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to persist project record after 3 attempts: {last_exc}",
                )

            try:
                # Determine delivery type (ZIP or HOSTED)
                delivery_type = session.get("metadata", {}).get("delivery_type", "ZIP").upper()
                stack_str = session.get("metadata", {}).get("tech_stack", "fastapi-react-postgres")

                # Factory Integration: Provision the tenant autonomously, with retry
                from backend.services.company_generator import (
                    CompanyGenerator,
                    CompanyRequest,
                    TechStack,
                )

                generator = CompanyGenerator()

                company_request = CompanyRequest(
                    name=f"Company-{project_id}",
                    description=f"Autonomously provisioned company for {customer_email}",
                    tech_stack=TechStack(stack_str),
                    features=["base-auth"],
                    user_id="STRIPE_CUSTOMER",
                )

                # Step 1: Generate Code (retry up to 3 times)
                gen_exc = None
                for attempt in range(1, 4):
                    try:
                        await generator.generate_company(company_request)
                        gen_exc = None
                        break
                    except Exception as exc:  # pylint: disable=broad-except
                        gen_exc = exc
                        logger.warning(
                            "generate_company attempt %d/3 failed for %s: %s",
                            attempt,
                            project_id,
                            exc,
                        )
                        if attempt < 3:
                            await asyncio.sleep(2**attempt)
                if gen_exc:
                    raise gen_exc

                # Step 2: Delivery Logic
                if delivery_type == "HOSTED":
                    logger.info("Delivery Mode: HOSTED. Provisioning VM on .tech domain...")
                    from backend.services.deployment_service import (
                        DeploymentService,
                        DeploymentConfig,
                    )

                    deploy_service = DeploymentService()

                    config = DeploymentConfig(
                        company_id=project_id,
                        tenant_name=f"box-{project_id.lower()}",
                        subdomain=project_id.lower(),
                    )

                    await deploy_service.create_deployment(config)
                    logger.info("Hosting subscription pending for %s", customer_email)

                    body = (
                        "<h1>Your SwarmOS Box is LIVE</h1>"
                        f"<p>Your autonomous company has been deployed to: "
                        f"<strong>https://{project_id.lower()}.realms2riches.tech</strong></p>"
                        "<p>Login with your Swarm credentials.</p>"
                    )
                else:
                    logger.info("Delivery Mode: ZIP. Creating bundle...")
                    bundle = replicator_engine.create_company_bundle(project_id)
                    body = (
                        "<h1>Your SwarmOS Box is Ready</h1>"
                        f"<p>Download your complete source code bundle: "
                        f"<a href='{bundle.get('download_url')}'>Here</a></p>"
                    )

                # Send Delivery Email
                email_sender = EmailTools()
                email_sender.send_email(
                    customer_email,
                    "Your Programmable Company Delivery",
                    body,
                )

            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(
                    "Failed to provision tenant or send email for project %s: %s",
                    project_id,
                    exc,
                )
                # Do not re-raise — project record was already persisted; delivery can be retried.

        # Mark event processed (idempotency guard)
        if event_id:
            try:
                DB.mark_event_processed(event_id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(
                    "Failed to mark event %s processed: %s",
                    event_id,
                    exc,
                )

    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to process Stripe webhook: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed",
        ) from exc

    return {"status": "success"}
