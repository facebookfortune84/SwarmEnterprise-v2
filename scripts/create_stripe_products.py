#!/usr/bin/env python3
"""
Create Stripe products and prices for three tiers.
Reads .env in repo root to load STRIPE_API_KEY.
"""

from pathlib import Path
import os

# Load .env
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

products = [
    ("Starter Box", 49900, 4900),
    ("Growth Box", 199900, 19900),
    ("Enterprise Box", 999900, 89900),
]

created = []
for name, one_time, monthly in products:
    prod = stripe.Product.create(name=name)
    one_time_price = stripe.Price.create(product=prod.id, unit_amount=one_time, currency="usd")
    monthly_price = stripe.Price.create(
        product=prod.id, unit_amount=monthly, currency="usd", recurring={"interval": "month"}
    )
    created.append((name, prod.id, one_time_price.id, monthly_price.id))
    print("Created:", name, prod.id, one_time_price.id, monthly_price.id)

# list recent webhooks
we = stripe.WebhookEndpoint.list(limit=5)
print("Webhooks:")
for w in we.data:
    print(w.id, w.url)
