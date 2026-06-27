#!/usr/bin/env python3
"""
generate_secrets.py -- SwarmEnterprise v2 cryptographic secret generator
RWV Techsolutions LLC - 1091 Harrison Ave Elkins, WV 26241
Contact: robertdemottojr50@gmail.com

Usage:
    python scripts/generate_secrets.py

    # Append directly to your .env (review before running in prod!):
    python scripts/generate_secrets.py >> .env

Generates a fresh set of strong random secrets and prints ready-to-paste
.env lines.  Run once per environment (dev / staging / prod) and store the
output in your secrets manager -- never reuse secrets across environments.

All values are generated with Python's `secrets` module (CSPRNG-backed).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------


def hex64() -> str:
    """64-character hex string -- 256 bits of entropy. Used for JWT/session keys."""
    return secrets.token_hex(32)  # 32 bytes -> 64 hex chars


def urlsafe32() -> str:
    """~43-character URL-safe base64 string from 32 bytes. Used for passwords."""
    return secrets.token_urlsafe(32)  # 32 bytes -> ~43 base64 chars


# ---------------------------------------------------------------------------
# Secret definitions
# ---------------------------------------------------------------------------
SECRETS: list[dict] = [
    {
        "key": "JWT_SECRET_KEY",
        "generator": hex64,
        "description": "64-char hex -- signs and verifies JWT access/refresh tokens",
        "rotate_days": 90,
    },
    {
        "key": "SECRET_KEY",
        "generator": hex64,
        "description": "64-char hex -- signs session cookies, CSRF tokens, and encrypted fields",
        "rotate_days": 90,
    },
    {
        "key": "POSTGRES_PASSWORD",
        "generator": urlsafe32,
        "description": "32-byte URL-safe -- Postgres superuser / application password",
        "rotate_days": 180,
    },
    {
        "key": "ENCRYPTION_KEY",
        "generator": urlsafe32,
        "description": "32-byte URL-safe -- symmetric encryption key for PII / stored secrets",
        "rotate_days": 365,
    },
]

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
_BANNER = (
    "# =============================================================================\n"
    "# SwarmEnterprise v2 -- Generated Secrets\n"
    "# RWV Techsolutions LLC - 1091 Harrison Ave Elkins, WV 26241\n"
    "# Generated : {ts}\n"
    "#\n"
    "# INSTRUCTIONS\n"
    "# ---------------------------------------------------------------------------\n"
    "# 1. Copy the KEY=VALUE lines below into your .env file.\n"
    "# 2. NEVER commit .env to version control.\n"
    "# 3. Store these values in your secrets manager (Vault / AWS Secrets Manager /\n"
    "#    GitHub Actions secrets) for staging and production environments.\n"
    "# 4. Generate a SEPARATE set for each environment (dev / staging / prod).\n"
    "# 5. Rotate on the schedule shown in the comments -- see:\n"
    "#    docs/guides/SECRETS_MANAGEMENT.md\n"
    "# =============================================================================\n"
)

_FOOTER = (
    "# =============================================================================\n"
    "# End of generated secrets.\n"
    "# Next steps:\n"
    "#   1. Paste the KEY=VALUE lines above into .env\n"
    "#   2. Run:  python scripts/validate_env.py\n"
    "#   3. Add remaining service credentials (Stripe, SMTP, etc.) -- see:\n"
    "#      docs/guides/SECRETS_MANAGEMENT.md\n"
    "# =============================================================================\n"
)


def main() -> None:
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(_BANNER.format(ts=ts))

    for spec in SECRETS:
        value = spec["generator"]()
        print("# {} -- rotate every {} days".format(spec["description"], spec["rotate_days"]))
        print("{}={}".format(spec["key"], value))
        print()

    print(_FOOTER)


if __name__ == "__main__":
    main()
