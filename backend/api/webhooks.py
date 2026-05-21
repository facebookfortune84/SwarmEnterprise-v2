"""
Stripe webhook processing for SwarmOS monetization.

This module handles incoming Stripe webhook events, validates signatures,
ensures idempotency, persists project records, triggers the Replicator
engine, and sends delivery emails when appropriate.
"""

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

            # Persist project record
            try:
                DB.create_project(
                    project_id,
                    stripe_session=session.get("id"),
                    customer_email=customer_email,
                    product_id=(
                        session.get("display_items", [])[0].get("price")
                        if session.get("display_items")
                        else None
                    ),
                    price_id=None,
                    metadata=str(session.get("metadata")),
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Failed to persist project record: %s", exc)

            # Trigger Replicator
            bundle = replicator_engine.create_company_bundle(project_id)

            if bundle and bundle.get("status") == "success":
                email_sender = EmailTools()
                body = (
                    "<h1>Your SwarmOS Box is Ready</h1>"
                    f"<p>Download: <a href='{bundle.get('download_url')}'>Here</a></p>"
                )
                email_sender.send_email(
                    customer_email,
                    "Your Programmable Company Delivery",
                    body,
                )

        # Mark event processed
        if event_id:
            try:
                DB.mark_event_processed(event_id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(
                    "Failed to mark event %s processed: %s",
                    event_id,
                    exc,
                )

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to process Stripe webhook: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed",
        ) from exc

    return {"status": "success"}
