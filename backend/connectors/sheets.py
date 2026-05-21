import os
import logging
from typing import Optional

logger = logging.getLogger("SheetsConnector")

# Lightweight Google Sheets connector using simple HTTP requests to Apps Script or Sheets API.
SHEETS_ENDPOINT = os.getenv(
    "SHEETS_ENDPOINT"
)  # Prefer an Apps Script webhook URL or internal sync endpoint


def push_row(payload: dict) -> Optional[dict]:
    if not SHEETS_ENDPOINT:
        logger.debug("SHEETS_ENDPOINT not configured; skipping sheets sync")
        return None
    try:
        import requests

        r = requests.post(
            SHEETS_ENDPOINT, json=payload, timeout=int(os.getenv("CONNECTOR_TIMEOUT", 10))
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.exception(f"Failed to push to Sheets endpoint: {e}")
        return None
