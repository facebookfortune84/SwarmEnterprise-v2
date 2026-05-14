import os
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("StripeAPI")
router = APIRouter(prefix="/api/stripe", tags=["Stripe"])

# Lazy import stripe to avoid import-time dependency issues
try:
    import stripe
except Exception:
    stripe = None

stripe.api_key = os.getenv("STRIPE_API_KEY")

class CheckoutCreate(BaseModel):
    product_name: str | None = None
    amount_cents: int | None = None
    price_id: str | None = None

@router.post("/create-checkout-session")
async def create_checkout_session(payload: CheckoutCreate):
    if stripe is None:
        raise HTTPException(status_code=500, detail="stripe library not available")

    try:
        # Determine success/cancel URLs from env
        frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
        success_url = f"{frontend}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend}/cancel"

        if payload.price_id:
            price_id = payload.price_id
        else:
            # Create product and price if not provided
            if not payload.product_name or not payload.amount_cents:
                raise HTTPException(status_code=400, detail="Either price_id or (product_name and amount_cents) required")
            product = stripe.Product.create(name=payload.product_name)
            price = stripe.Price.create(product=product.id, unit_amount=payload.amount_cents, currency="usd")
            price_id = price.id

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return {"url": session.url, "id": session.id}
    except stripe.error.StripeError as e:
        logger.exception("Stripe API error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error creating checkout session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    if stripe is None:
        raise HTTPException(status_code=500, detail="stripe library not available")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        # Invalid payload
        logger.error("Invalid payload for Stripe webhook: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature for Stripe webhook: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session.get("id")
        customer_email = None
        try:
            customer_details = session.get('customer_details') or {}
            customer_email = customer_details.get('email')
        except Exception:
            customer_email = None

        # Project metadata may be passed in session.metadata
        metadata = session.get('metadata') or {}
        product_id = None
        price_id = None
        # Inspect line_items if available (may require expanded event)
        try:
            # Create a project record and enqueue build
            import uuid
            project_id = f"PROJ-{uuid.uuid4().hex[:6].upper()}"
            from backend.db.linear_engine import get_swarm_db
            db = get_swarm_db()
            db.create_project(project_id=project_id, stripe_session=session_id, customer_email=customer_email, product_id=product_id, price_id=price_id, metadata=str(metadata))

            # Record a usage event for billing/analytics
            try:
                db.record_usage(project_id, event_type='purchase', amount=str(metadata.get('amount')) if metadata.get('amount') else None, metadata={'session_id': session_id})
            except Exception:
                logger.exception("Failed to record usage event for purchase")

            # Trigger the build asynchronously
            import asyncio
            from backend.core.factory import swarm_factory
            description = metadata.get('description') or f"Stripe purchase {session_id}"
            # run production cycle in background
            asyncio.create_task(asyncio.to_thread(swarm_factory.run_production_cycle, project_id, description))

            logger.info("Stripe checkout completed and project created: %s -> %s", session_id, project_id)
        except Exception as e:
            logger.exception("Failed to create project or enqueue build: %s", e)

    return {"status": "received"}
