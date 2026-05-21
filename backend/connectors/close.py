import os
import requests
import logging
from typing import Optional

logger = logging.getLogger("CloseConnector")
API_KEY = os.getenv("CLOSE_API_KEY")
BASE = os.getenv("CLOSE_API_BASE", "https://api.close.com/api/v1")
TIMEOUT = int(os.getenv("CONNECTOR_TIMEOUT", 10))


def create_lead(email: str, properties: dict) -> Optional[dict]:
    if not API_KEY:
        logger.debug("CLOSE_API_KEY not configured; skipping Close sync")
        return None
    url = f"{BASE}/lead/"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    payload = {
        "name": properties.get("name") or email,
        "contacts": [{"emails": [email]}],
        "custom": properties,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.exception(f"Failed to create Close lead: {e}")
        return None
