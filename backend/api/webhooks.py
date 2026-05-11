import os
import stripe
import logging
from fastapi import APIRouter, Request, Header, HTTPException
from backend.replicator import replicator_engine
from agents.outreach.email_engine import EmailTools

router = APIRouter(prefix="/api/webhooks", tags=["Monetization"])
logger = logging.getLogger("SwarmWebhooks")

stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_placeholder")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

@router.post("/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except Exception as e:
        logger.error(f"Stripe signature failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email')
        project_id = session.get('metadata', {}).get('project_id', 'DEFAULT')
        
        logger.info(f"PAYMENT RECEIVED from {customer_email}. Delivering Box...")
        
        # Trigger Replicator
        bundle = replicator_engine.create_company_bundle(project_id)
        
        if bundle['status'] == 'success':
            email_sender = EmailTools()
            body = f"<h1>Your SwarmOS Box is Ready</h1><p>Download: <a href='{bundle['download_url']}'>Here</a></p>"
            email_sender.send_email(customer_email, "Your Programmable Company Delivery", body)
            
    return {"status": "success"}
