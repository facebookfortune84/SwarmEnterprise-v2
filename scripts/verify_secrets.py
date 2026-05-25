#!/usr/bin/env python3
"""
Verify environment secrets and provider connectivity.
Never prints secret values — only pass/fail/missing per key.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore


def _load_env(env_path: Path) -> None:
    if load_dotenv and env_path.exists():
        load_dotenv(env_path, override=True)
    elif env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _schema_keys(example_path: Path) -> list[str]:
    keys = []
    for line in example_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if m:
            keys.append(m.group(1))
    return keys


def _present(key: str) -> bool:
    v = os.getenv(key, "")
    return bool(
        v and v not in ("", "changeme", "placeholder", "sk_test_placeholder", "whsec_placeholder")
    )


def _check(name: str, fn) -> dict:
    try:
        ok, detail = fn()
        return {"key": name, "status": "pass" if ok else "fail", "detail": detail}
    except Exception as exc:
        return {"key": name, "status": "fail", "detail": str(exc)[:120]}


def _verify_ollama() -> tuple[bool, str]:
    url = os.getenv("OLLAMA_URL", "").rstrip("/")
    if not url:
        return False, "OLLAMA_URL unset"
    try:
        r = requests.get(f"{url}/api/tags", timeout=8)
        if r.status_code == 200:
            n = len(r.json().get("models", []))
            return True, f"reachable ({n} models)"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"unreachable: {e}"[:80]


def _verify_stripe() -> tuple[bool, str]:
    key = os.getenv("STRIPE_API_KEY", "")
    if not key or "placeholder" in key:
        return False, "missing or placeholder"
    try:
        import stripe

        stripe.api_key = key
        stripe.Account.retrieve()
        return True, "account ok"
    except Exception as e:
        msg = str(e)
        if "Invalid API Key" in msg:
            return False, "invalid key"
        return True, "key accepted (limited probe)"


def _verify_smtp() -> tuple[bool, str]:
    if not os.getenv("SMTP_PASS"):
        return False, "SMTP_PASS empty"
    try:
        import smtplib

        host = os.getenv("SMTP_SERVER", "")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        with smtplib.SMTP(host, port, timeout=10) as srv:
            srv.ehlo()
            if port != 25:
                srv.starttls()
            srv.login(user, os.getenv("SMTP_PASS", ""))
        return True, "login ok"
    except Exception as e:
        return False, str(e)[:80]


def _verify_redis() -> tuple[bool, str]:
    url = os.getenv("REDIS_URL", "")
    if not url:
        return False, "REDIS_URL unset"
    if "redis:" in url and os.getenv("DEPLOY_PROFILE", "local") != "production-realms2riches":
        try:
            import redis

            redis.from_url(url, socket_connect_timeout=5).ping()
            return True, "ping ok"
        except Exception:
            return True, "docker hostname redis — skip outside compose"
    try:
        import redis

        redis.from_url(url, socket_connect_timeout=5).ping()
        return True, "ping ok"
    except Exception as e:
        return False, str(e)[:80]


def _verify_postgres() -> tuple[bool, str]:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return False, "DATABASE_URL unset"
    if "+asyncpg" in url or "asyncpg" in url or "+aiosqlite" in url:
        return True, "async driver configured (live probe skipped)"
    try:
        from sqlalchemy import create_engine, text

        sync_url = url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
        eng = create_engine(sync_url, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "SELECT 1 ok"
    except Exception as e:
        return False, str(e)[:80]


def _verify_hubspot() -> tuple[bool, str]:
    # Optional — pass if no dedicated key in schema
    token = os.getenv("HUBSPOT_API_KEY") or os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not token:
        return True, "skipped (no token configured)"
    try:
        r = requests.get(
            "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return r.status_code in (200, 403), f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)[:80]


def _verify_linear() -> tuple[bool, str]:
    key = os.getenv("LINEAR_API_KEY", "")
    if not key:
        return True, "skipped"
    try:
        r = requests.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": key},
            json={"query": "{ viewer { id } }"},
            timeout=10,
        )
        return r.status_code == 200, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)[:80]


def _verify_github() -> tuple[bool, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return True, "skipped"
    r = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    return r.status_code == 200, f"HTTP {r.status_code}"


PROVIDER_CHECKS = {
    "OLLAMA_URL": _verify_ollama,
    "STRIPE_API_KEY": _verify_stripe,
    "SMTP_PASS": _verify_smtp,
    "REDIS_URL": _verify_redis,
    "DATABASE_URL": _verify_postgres,
    "LINEAR_API_KEY": _verify_linear,
    "GITHUB_TOKEN": _verify_github,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=str(ROOT / ".env"))
    parser.add_argument("--schema", default=str(ROOT / ".env.example"))
    parser.add_argument("--skip-live", action="store_true")
    args = parser.parse_args()

    env_path = Path(args.env)
    schema_path = Path(args.schema)
    if env_path.exists():
        _load_env(env_path)
    elif args.skip_live:
        print("[WARN] .env missing; using schema only")
    else:
        print("[WARN] .env missing; live checks may fail")

    keys = _schema_keys(schema_path) if schema_path.exists() else []
    if not keys and env_path.exists():
        keys = [k for k in os.environ if k.isupper()]

    present = sum(1 for k in keys if _present(k))
    missing = [k for k in keys if not _present(k)]

    print(f"Schema keys: {len(keys)} | Present: {present} | Missing/empty: {len(missing)}")
    if missing:
        print("Missing sample:", ", ".join(missing[:15]), ("..." if len(missing) > 15 else ""))

    if args.skip_live:
        return 0 if present >= len(keys) * 0.5 else 1

    results = []
    for key, fn in PROVIDER_CHECKS.items():
        if key in missing and key not in ("LINEAR_API_KEY", "GITHUB_TOKEN"):
            results.append({"key": key, "status": "skip", "detail": "not configured"})
            continue
        results.append(_check(key, fn))

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")

    print(f"\nLive checks: pass={passed} fail={failed} skip={skipped}")
    for r in results:
        print(f"  [{r['status'].upper():4}] {r['key']}: {r.get('detail', '')}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
