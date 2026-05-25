#!/usr/bin/env python3
"""
Create a Stripe product + price and print IDs. Reads .env in repo root to load STRIPE_API_KEY.
Use with caution: this will call Stripe API using keys found in .env.
"""

import os
from pathlib import Path

# Load .env manually (simple parser)
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

stripe_key = os.getenv("STRIPE_API_KEY")
if not stripe_key:
    print("STRIPE_API_KEY not found in environment or .env")
    raise SystemExit(1)

try:
    import stripe
except Exception as e:
    print("stripe library not available:", e)
    raise

stripe.api_key = stripe_key

# Create product
product = stripe.Product.create(name="SwarmEnterprise Demo Product")
price = stripe.Price.create(product=product.id, unit_amount=100, currency="usd")
print("product_id=", product.id)
print("price_id=", price.id)

# Create checkout session
frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
success_url = f"{frontend}/success?session_id={{CHECKOUT_SESSION_ID}}"
cancel_url = f"{frontend}/cancel"

session = stripe.checkout.Session.create(
    payment_method_types=["card"],
    line_items=[{"price": price.id, "quantity": 1}],
    mode="payment",
    success_url=success_url,
    cancel_url=cancel_url,
)
print("session_id=", session.id)
print("session_url=", session.url)
