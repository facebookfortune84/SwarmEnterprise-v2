#!/usr/bin/env python3
"""
validate_env.py -- SwarmEnterprise v2 environment variable validator
RWV Techsolutions LLC - 1091 Harrison Ave Elkins, WV 26241
Contact: robertdemottojr50@gmail.com

Usage:
    python scripts/validate_env.py              # reads .env from project root
    python scripts/validate_env.py --env /path/to/.env
    python scripts/validate_env.py --no-color   # plain output for CI logs

Exits 0 if all critical variables are present, 1 if any are missing.
Never prints secret values -- only present / missing status.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Optional python-dotenv -- fall back to manual parser if not installed
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv as _load_dotenv

    def _load_env(path: Path) -> None:
        _load_dotenv(path, override=True)

except ImportError:
    def _load_env(path: Path) -> None:  # type: ignore[misc]
        """Minimal .env parser (no python-dotenv installed)."""
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            # Strip optional inline comments and quotes
            val = val.split(" #")[0].strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), val)


# ---------------------------------------------------------------------------
# Service group definitions  (critical=True -> failure exits with code 1)
# ---------------------------------------------------------------------------
class VarSpec(NamedTuple):
    name: str
    critical: bool = True
    description: str = ""


GROUPS: dict[str, list[VarSpec]] = {
    "Database (PostgreSQL)": [
        VarSpec("DATABASE_URL",        True,  "Full Postgres connection string"),
        VarSpec("POSTGRES_PASSWORD",   True,  "Postgres user password"),
        VarSpec("POSTGRES_USER",       True,  "Postgres username"),
        VarSpec("POSTGRES_DB",         True,  "Postgres database name"),
    ],
    "Redis": [
        VarSpec("REDIS_URL",           True,  "Redis connection URL"),
    ],
    "Stripe (Payments)": [
        VarSpec("STRIPE_API_KEY",          True,  "Stripe secret key (sk_live_... or sk_test_...)"),
        VarSpec("STRIPE_WEBHOOK_SECRET",   True,  "Stripe webhook signing secret (whsec_...)"),
        VarSpec("STRIPE_PUBLISHABLE_KEY",  True,  "Stripe publishable key (pk_live_... or pk_test_...)"),
    ],
    "SMTP (Email)": [
        VarSpec("SMTP_USER",    True,  "SMTP login username / email address"),
        VarSpec("SMTP_PASS",    True,  "SMTP login password or app password"),
        VarSpec("SMTP_SERVER",  True,  "SMTP host (e.g. smtp.gmail.com)"),
        VarSpec("SMTP_PORT",    True,  "SMTP port (587=STARTTLS, 465=SSL)"),
    ],
    "JWT / Auth (Security)": [
        VarSpec("JWT_SECRET_KEY",  True,  "64-char hex secret for JWT signing"),
        VarSpec("SECRET_KEY",      True,  "64-char hex secret for session / cookie signing"),
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PLACEHOLDER_VALUES = {
    "", "changeme", "placeholder", "your-secret-here",
    "sk_test_placeholder", "whsec_placeholder", "todo", "xxxx",
}

# ANSI colors -- silenced when --no-color is passed or stdout is not a TTY
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# Check / cross icons -- fall back to ASCII if terminal can't handle UTF-8
_ICON_OK   = "[OK]"
_ICON_FAIL = "[!!]"
try:
    "pass".encode(sys.stdout.encoding or "ascii")
    # If we get here the encoding is usable; now check if it supports checkmarks
    "[OK][!!]".encode(sys.stdout.encoding or "ascii")
    _ICON_OK   = "[OK]"
    _ICON_FAIL = "[!!]"
except (UnicodeEncodeError, TypeError, LookupError):
    pass


def _is_set(key: str) -> bool:
    val = os.getenv(key, "").strip()
    return bool(val) and val.lower() not in PLACEHOLDER_VALUES


def _icon(ok: bool) -> str:
    if ok:
        return "{}{}{}".format(GREEN, _ICON_OK, RESET)
    return "{}{}{}".format(RED, _ICON_FAIL, RESET)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - len(s))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate SwarmEnterprise v2 environment variables."
    )
    parser.add_argument(
        "--env",
        default=str(ROOT / ".env"),
        help="Path to .env file (default: <project-root>/.env)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output (useful in CI logs)",
    )
    args = parser.parse_args()

    # Disable color if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        global GREEN, RED, YELLOW, BOLD, RESET  # noqa: PLW0603
        GREEN = RED = YELLOW = BOLD = RESET = ""

    env_path = Path(args.env)
    if env_path.exists():
        _load_env(env_path)
        print("{}Loaded:{} {}\n".format(BOLD, RESET, env_path))
    else:
        print("{}[WARN]{} .env not found at {} -- checking process environment only.\n".format(
            YELLOW, RESET, env_path))

    any_critical_fail = False
    all_pass = True

    # Column width for aligned output
    max_key_len = max(
        len(v.name)
        for specs in GROUPS.values()
        for v in specs
    )

    for group_name, specs in GROUPS.items():
        group_ok = all(_is_set(v.name) for v in specs)
        group_icon = _icon(group_ok)
        print("{}{}  {}{}".format(BOLD, group_icon, group_name, RESET))

        for spec in specs:
            ok = _is_set(spec.name)
            icon = _icon(ok)
            padded_key = _pad(spec.name, max_key_len)
            hint = "  # {}".format(spec.description) if spec.description else ""
            print("     {}  {}{}".format(icon, padded_key, hint))

            if not ok:
                all_pass = False
                if spec.critical:
                    any_critical_fail = True

        print()

    # Summary
    print("-" * 60)
    if all_pass:
        print("{}{}All required variables are set. {}{}".format(
            GREEN, BOLD, "[OK]", RESET))
        return 0

    critical_missing = [
        v.name
        for specs in GROUPS.values()
        for v in specs
        if v.critical and not _is_set(v.name)
    ]
    optional_missing = [
        v.name
        for specs in GROUPS.values()
        for v in specs
        if not v.critical and not _is_set(v.name)
    ]

    if critical_missing:
        print("{}{}Critical variables missing ({}):{} ".format(
            RED, BOLD, len(critical_missing), RESET))
        for k in critical_missing:
            print("  {}*{} {}".format(RED, RESET, k))
        print()
    if optional_missing:
        print("{}Optional variables unset ({}):{} ".format(
            YELLOW, len(optional_missing), RESET))
        for k in optional_missing:
            print("  {}-{} {}".format(YELLOW, RESET, k))
        print()

    print("Run {}python scripts/generate_secrets.py{} to generate secure values.".format(
        BOLD, RESET))
    print("See docs/guides/SECRETS_MANAGEMENT.md for setup instructions.")

    return 1 if any_critical_fail else 0


if __name__ == "__main__":
    sys.exit(main())
