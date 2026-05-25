#!/usr/bin/env python3
from pathlib import Path
import os

# load .env
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import stripe  # noqa: E402

stripe.api_key = os.getenv("STRIPE_API_KEY")
backend = os.getenv("BACKEND_URL", "http://localhost:8000")
url = backend.rstrip("/") + "/api/stripe/webhook"
print("Creating webhook endpoint for URL:", url)
we = stripe.WebhookEndpoint.create(url=url, enabled_events=["checkout.session.completed"])
print("id=", we.id)
print("secret=", we.secret)
