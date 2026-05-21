"""Minimal API smoke test (no external services required)."""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("STRIPE_API_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
os.environ.setdefault("OTEL_SDK_DISABLED", "TRUE")

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


def main() -> int:
    client = TestClient(app)
    health = client.get("/health")
    if health.status_code != 200:
        print(f"[FAIL] /health -> {health.status_code}")
        return 1
    body = health.json()
    if body.get("status") != "ONLINE":
        print(f"[FAIL] unexpected health body: {body}")
        return 1
    print("[OK] /health", body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
