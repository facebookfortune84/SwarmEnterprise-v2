"""
Stripe checkout session API.

This module exposes endpoints for creating Stripe Checkout sessions.
It supports both predefined price IDs and dynamic product/price creation.
"""

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Lazy import to avoid hard dependency at import time
try:
    import stripe
except Exception:  # pylint: disable=broad-except
    stripe = None

router = APIRouter(prefix="/api/stripe", tags=["Stripe"])
logger = logging.getLogger("StripeAPI")

# Configure Stripe API key if available
if stripe is not None:
    stripe.api_key = os.getenv("STRIPE_API_KEY")


class CheckoutCreate(BaseModel):
    """Payload for creating a Stripe checkout session."""

    product_name: str | None = None
    amount_cents: int | None = None
    price_id: str | None = None


@router.post("/create-checkout-session")
async def create_checkout_session(payload: CheckoutCreate):
    """
    Create a Stripe Checkout session.

    Args:
        payload (CheckoutCreate): Product or price information.

    Raises:
        HTTPException: If Stripe is unavailable or request is invalid.

    Returns:
        dict: Checkout session URL and ID.
    """
    if stripe is None:
        raise HTTPException(
            status_code=500,
            detail="Stripe library not available",
        )

    try:
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        success_url = f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/cancel"

        # Use existing price ID if provided
        if payload.price_id:
            price_id = payload.price_id
        else:
            # Validate dynamic product creation
            if not payload.product_name or not payload.amount_cents:
                raise HTTPException(
                    status_code=400,
                    detail=("Either price_id or " "(product_name and amount_cents) is required"),
                )

            product = stripe.Product.create(name=payload.product_name)
            price = stripe.Price.create(
                product=product.id,
                unit_amount=payload.amount_cents,
                currency="usd",
            )
            price_id = price.id

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return {"url": session.url, "id": session.id}

    except stripe.error.StripeError as exc:
        logger.exception("Stripe API error: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unexpected error creating checkout session: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
