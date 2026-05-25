import os
import requests
import logging

logger = logging.getLogger("Alerting")

PAGERDUTY_ROUTING_KEY = os.getenv("PAGERDUTY_ROUTING_KEY")


def send_pagerduty_alert(summary: str, severity: str = "error") -> bool:
    if not PAGERDUTY_ROUTING_KEY:
        logger.debug("PagerDuty not configured; skipping alert")
        return False
    payload = {
        "routing_key": PAGERDUTY_ROUTING_KEY,
        "event_action": "trigger",
        "payload": {"summary": summary, "severity": severity, "source": "swarmos"},
    }
    try:
        r = requests.post("https://events.pagerduty.com/v2/enqueue", json=payload, timeout=5)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.exception(f"Failed to send PagerDuty alert: {e}")
        return False
