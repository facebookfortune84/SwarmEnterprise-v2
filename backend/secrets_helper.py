import os
import logging

logger = logging.getLogger("secrets_helper")

# Minimal helper to fetch secrets from common sources.
# In production, replace with a full secrets manager integration.

def get_secret(name: str) -> str | None:
    # Priority: environment variable -> file at /run/secrets/{name} -> None
    v = os.getenv(name)
    if v:
        return v
    path = f"/run/secrets/{name}"
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except Exception:
            logger.exception(f"Failed reading secret file {path}")
    return None

# Example usage: STRIPE_API_KEY = get_secret('STRIPE_API_KEY') or os.getenv('STRIPE_API_KEY')
