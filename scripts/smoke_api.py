"""
SwarmEnterprise v2 — API smoke tests.

Runs against a live server (default: http://localhost:8000) using real HTTP
requests, or falls back to FastAPI's TestClient for fully in-process testing.

Usage
-----
# In-process (no server needed):
    python scripts/smoke_api.py

# Against a running server:
    python scripts/smoke_api.py --base-url http://localhost:8000
    python scripts/smoke_api.py --base-url https://realms2riches.com --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from typing import Any

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("STRIPE_API_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
os.environ.setdefault("OTEL_SDK_DISABLED", "TRUE")

# ---------------------------------------------------------------------------
# Client abstraction
# ---------------------------------------------------------------------------

class _HttpClient:
    """Thin wrapper so tests are identical for in-process and live modes."""

    def __init__(self, base_url: str | None) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._live = bool(self._base_url)
        if not self._live:
            from fastapi.testclient import TestClient
            from backend.main import app
            self._client: Any = TestClient(app, raise_server_exceptions=False)
        else:
            import urllib.request  # stdlib only — no extra deps
            self._client = None

    # ------------------------------------------------------------------
    def _live_request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[int, Any]:
        import json as json_mod
        import urllib.error
        import urllib.request

        url = f"{self._base_url}{path}"
        body: bytes | None = None
        req_headers = dict(headers or {})

        if json is not None:
            body = json_mod.dumps(json).encode()
            req_headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode(errors="replace")
                code = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            code = exc.code

        try:
            parsed = json_mod.loads(raw)
        except Exception:
            parsed = raw
        return code, parsed

    # ------------------------------------------------------------------
    def get(self, path: str, headers: dict | None = None) -> tuple[int, Any]:
        if self._live:
            return self._live_request("GET", path, headers=headers)
        resp = self._client.get(path, headers=headers or {})
        return resp.status_code, _safe_json(resp)

    def post(self, path: str, json: dict | None = None, headers: dict | None = None) -> tuple[int, Any]:
        if self._live:
            return self._live_request("POST", path, json=json, headers=headers)
        resp = self._client.post(path, json=json, headers=headers or {})
        return resp.status_code, _safe_json(resp)


def _safe_json(resp: Any) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

_PASS = 0
_FAIL = 0
_VERBOSE = False


def _result(label: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    tag = "[PASS]" if ok else "[FAIL]"
    suffix = f"  — {detail}" if detail else ""
    print(f"{tag} {label}{suffix}")
    if ok:
        _PASS += 1
    else:
        _FAIL += 1


def _assert(label: str, condition: bool, detail: str = "") -> bool:
    _result(label, condition, detail)
    return condition


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def test_health(client: _HttpClient) -> None:
    """GET /health — expect 200 and status == ONLINE."""
    code, body = client.get("/health")
    ok_code = _assert("GET /health → 200", code == 200, f"got {code}")
    if ok_code:
        status_val = body.get("status") if isinstance(body, dict) else None
        _assert(
            'GET /health body.status == "ONLINE"',
            status_val == "ONLINE",
            f"got {status_val!r}",
        )
        if _VERBOSE:
            print(f"       body: {body}")


def test_metrics(client: _HttpClient) -> None:
    """GET /metrics — expect 200."""
    code, body = client.get("/metrics")
    _assert("GET /metrics → 200", code == 200, f"got {code}")
    if _VERBOSE:
        snippet = str(body)[:120] if body else ""
        print(f"       body (truncated): {snippet}")


def test_docs(client: _HttpClient) -> None:
    """GET /docs — expect 200 (Swagger UI is live)."""
    code, _ = client.get("/docs")
    _assert("GET /docs (Swagger UI) → 200", code == 200, f"got {code}")


def test_auth_flow(client: _HttpClient) -> str | None:
    """
    Full auth flow:
      1. POST /api/auth/register  → 201 + tokens
      2. POST /api/auth/login     → 200 + access_token
      3. GET  /api/auth/verify    → 200 (authenticated)

    Returns the access token on success, None on failure.
    """
    email = f"smoke_{uuid.uuid4().hex[:8]}@test.invalid"
    password = f"SmokePass#{int(time.time())}"
    full_name = "Smoke Test User"

    # -- register --
    code, body = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    ok_reg = _assert("POST /api/auth/register → 201", code == 201, f"got {code}")
    if ok_reg and isinstance(body, dict):
        has_token = "access_token" in body
        _assert("POST /api/auth/register body has access_token", has_token)
    if _VERBOSE:
        print(f"       body: {body}")

    # -- login --
    code, body = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    ok_login = _assert("POST /api/auth/login → 200", code == 200, f"got {code}")

    token: str | None = None
    if ok_login and isinstance(body, dict):
        token = body.get("access_token")
        _assert("POST /api/auth/login body has access_token", bool(token))
    if _VERBOSE:
        print(f"       body: {body}")

    if not token:
        _result("GET /api/auth/verify (authenticated) → 200", False, "skipped — no token")
        return None

    # -- verify token --
    code, body = client.get(
        "/api/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert("GET /api/auth/verify (authenticated) → 200", code == 200, f"got {code}")
    if _VERBOSE:
        print(f"       body: {body}")

    return token


def test_companies_authenticated(client: _HttpClient, token: str) -> None:
    """GET /api/companies/ with a valid token — expect 200."""
    code, body = client.get(
        "/api/companies/",
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert("GET /api/companies/ (authenticated) → 200", code == 200, f"got {code}")
    if _VERBOSE:
        print(f"       body: {body}")


def test_companies_unauthenticated(client: _HttpClient) -> None:
    """GET /api/companies/ without token — expect 401 or 403 (auth guard active)."""
    code, _ = client.get("/api/companies/")
    _assert(
        "GET /api/companies/ (no token) → 401/403",
        code in (401, 403),
        f"got {code}",
    )


def test_stripe_checkout_route_exists(client: _HttpClient) -> None:
    """
    GET /api/stripe/create-checkout-session — expect 405 Method Not Allowed.
    This proves the Stripe router is mounted and the route exists
    (the actual endpoint only accepts POST).
    """
    code, _ = client.get("/api/stripe/create-checkout-session")
    _assert(
        "GET /api/stripe/create-checkout-session → 405 (route exists)",
        code == 405,
        f"got {code}",
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    global _VERBOSE

    parser = argparse.ArgumentParser(
        description="SwarmEnterprise v2 API smoke tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--base-url",
        metavar="URL",
        default="",
        help=(
            "Base URL of a running server (e.g. http://localhost:8000). "
            "Omit to run in-process via FastAPI TestClient."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print full response bodies for each test.",
    )
    args = parser.parse_args(argv)
    _VERBOSE = args.verbose

    client = _HttpClient(args.base_url or None)
    mode = f"live → {args.base_url}" if args.base_url else "in-process (TestClient)"

    print()
    print("SwarmEnterprise v2 — API Smoke Tests")
    print(f"Mode : {mode}")
    print("─" * 60)

    # Core infrastructure
    test_health(client)
    test_metrics(client)
    test_docs(client)

    # Auth flow (register → login → verify)
    token = test_auth_flow(client)

    # Authenticated company list
    if token:
        test_companies_authenticated(client, token)
    else:
        _result("GET /api/companies/ (authenticated) → 200", False, "skipped — auth failed")

    # Guard check (unauthenticated)
    test_companies_unauthenticated(client)

    # Stripe router mount check
    test_stripe_checkout_route_exists(client)

    # Summary
    total = _PASS + _FAIL
    print("─" * 60)
    print(f"Results: {_PASS} passed / {_FAIL} failed / {total} total")
    print()
    if _FAIL:
        print("SMOKE TEST FAILED")
        return 1
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
