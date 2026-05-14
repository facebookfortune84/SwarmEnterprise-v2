import os
import requests
import logging
from typing import Optional

logger = logging.getLogger("HubSpotConnector")

API_KEY = os.getenv("HUBSPOT_API_KEY")
BASE = os.getenv("HUBSPOT_API_BASE", "https://api.hubapi.com")
TIMEOUT = int(os.getenv("CONNECTOR_TIMEOUT", 10))


def create_contact(email: str, properties: dict) -> Optional[dict]:
    """Create or update a HubSpot contact. Returns contact payload or None on failure."""
    if not API_KEY:
        logger.debug("HUBSPOT_API_KEY not configured; skipping hubspot sync")
        return None
    url = f"{BASE}/crm/v3/objects/contacts"
    headers = {"Content-Type": "application/json"}
    params = {"hapikey": API_KEY}
    payload = {"properties": {"email": email, **properties}}

    try:
        r = requests.post(url, json=payload, headers=headers, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.exception(f"Failed to create HubSpot contact: {e}")
        return None
