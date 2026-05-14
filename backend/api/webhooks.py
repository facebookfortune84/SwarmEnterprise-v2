import os
import uuid
import stripe
import logging
from fastapi import APIRouter, Request, HTTPException
from backend.replicator import replicator_engine
from agents.outreach.email_engine import EmailTools
from backend.db.linear_engine import get_swarm_db

router = APIRouter(prefix="/api/webhooks", tags=["Monetization"])
logger = logging.getLogger("SwarmWebhooks")

stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

_db = get_swarm_db()

@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")
    if not sig:
        logger.error("Missing Stripe signature header")
        raise HTTPException(status_code=400, detail="Missing signature header")

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.exception(f"Error parsing webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_id = event.get('id')
    if event_id and _db.is_event_processed(event_id):
        logger.info(f"Duplicate event received: {event_id}")
        return {"status": "success", "note": "already_processed"}

    try:
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_email = session.get('customer_details', {}).get('email')
            project_id = session.get('metadata', {}).get('project_id') or uuid.uuid4().hex[:8].upper()

            logger.info(f"PAYMENT RECEIVED from {customer_email}. Delivering Box for project {project_id}...")

            # Persist project record for auditing
            try:
                _db.create_project(project_id, stripe_session=session.get('id'), customer_email=customer_email, product_id=session.get('display_items', [])[0].get('price') if session.get('display_items') else None, price_id=None, metadata=str(session.get('metadata')))
            except Exception:
                logger.exception("Failed to persist project record")

            # Trigger Replicator
            bundle = replicator_engine.create_company_bundle(project_id)

            if bundle and bundle.get('status') == 'success':
                email_sender = EmailTools()
                body = f"<h1>Your SwarmOS Box is Ready</h1><p>Download: <a href='{bundle.get('download_url')}'>Here</a></p>"
                email_sender.send_email(customer_email, "Your Programmable Company Delivery", body)

        # Mark event processed for idempotency
        if event_id:
            try:
                _db.mark_event_processed(event_id)
            except Exception:
                logger.exception(f"Failed to mark event {event_id} processed")

    except Exception as e:
        logger.exception(f"Failed to process stripe webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "success"}
