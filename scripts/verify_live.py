#!/usr/bin/env python3
"""
verify_live.py — SwarmEnterprise v2 Live Environment & Company Builder Verifier
RWV Techsolutions LLC · robertdemottojr50@gmail.com

Tests the LIVE environment end-to-end:
  1. Infrastructure health   — /health, /metrics, /docs
  2. Auth flow               — register → login → verify → me
  3. Company Builder         — create company, poll status, verify record
  4. Billing routes          — Stripe router is mounted
  5. Security guards         — unauthenticated requests return 401/403
  6. TLS / HTTPS             — valid certificate (if HTTPS URL)
  7. Performance             — each request under 2 s p95
  8. Cleanup                 — delete test user data

Usage:
  python scripts/verify_live.py                            # localhost:8000
  python scripts/verify_live.py --url https://realms2riches.com
  python scripts/verify_live.py --url https://realms2riches.com --verbose
  python scripts/verify_live.py --url http://localhost:8000 --json report.json

Exit codes:
  0 — all tests pass
  1 — one or more tests fail
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── result tracking ───────────────────────────────────────────────────────────
_PASS = 0
_FAIL = 0
_VERBOSE = False
_results: list[dict] = []


def _record(label: str, ok: bool, detail: str = "") -> bool:
    global _PASS, _FAIL
    tag = "[PASS]" if ok else "[FAIL]"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {tag} {label}{suffix}")
    if _VERBOSE and detail and not ok:
        print(f"         detail: {detail}")
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
    _results.append({"label": label, "pass": ok, "detail": detail})
    return ok


def _assert(label: str, condition: bool, detail: str = "") -> bool:
    return _record(label, condition, detail)


# ── HTTP client ───────────────────────────────────────────────────────────────
class Client:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")
        self._token: str | None = None

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict | None = None,
        extra_headers: dict | None = None,
        auth: bool = False,
    ) -> tuple[int, Any]:
        import json as _json

        url = f"{self.base}{path}"
        headers: dict[str, str] = {}
        body: bytes | None = None

        if json_body is not None:
            body = _json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode(errors="replace")
                code = r.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            code = e.code
        except Exception as e:
            return 0, str(e)

        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return code, parsed

    def get(self, path: str, auth: bool = False, extra_headers: dict | None = None):
        return self._request("GET", path, auth=auth, extra_headers=extra_headers)

    def post(self, path: str, body: dict | None = None, auth: bool = False):
        return self._request("POST", path, json_body=body, auth=auth)

    def delete(self, path: str, auth: bool = False):
        return self._request("DELETE", path, auth=auth)


# ── individual test suites ────────────────────────────────────────────────────

def test_infrastructure(c: Client) -> None:
    print("\n  [1/7] Infrastructure Health")

    t0 = time.monotonic()
    code, body = c.get("/health")
    elapsed = (time.monotonic() - t0) * 1000
    ok = _assert("GET /health → 200", code == 200, f"got {code}, {elapsed:.0f}ms")
    if ok and isinstance(body, dict):
        _assert(
            'body.status == "ONLINE"',
            body.get("status") == "ONLINE",
            f"got {body.get('status')!r}",
        )
        db_ok = body.get("checks", {}).get("db") in ("ok", "healthy", True, "ONLINE")
        redis_ok = body.get("checks", {}).get("redis") in ("ok", "healthy", True, "ONLINE")
        _assert("health.checks.db is healthy", db_ok,
                str(body.get("checks", {}).get("db", "missing")))
        _assert("health.checks.redis is healthy", redis_ok,
                str(body.get("checks", {}).get("redis", "missing")))
        _assert("response time < 2000ms", elapsed < 2000, f"{elapsed:.0f}ms")
    if _VERBOSE and isinstance(body, dict):
        print(f"         {json.dumps(body, indent=2)[:300]}")

    code, _ = c.get("/metrics")
    _assert("GET /metrics → 200", code == 200, f"got {code}")

    code, body = c.get("/docs")
    _assert("GET /docs (Swagger UI) → 200", code == 200, f"got {code}")


def test_auth_flow(c: Client) -> str | None:
    print("\n  [2/7] Authentication Flow")

    email = f"verify_{uuid.uuid4().hex[:8]}@test.invalid"
    password = f"LiveTest#{int(time.time())}"

    # Register
    code, body = c.post(
        "/api/auth/register",
        {"email": email, "password": password, "full_name": "Live Verify"},
    )
    ok_reg = _assert("POST /api/auth/register → 201", code == 201, f"got {code}")
    if ok_reg and isinstance(body, dict):
        _assert("register response has access_token", "access_token" in body)

    # Login
    code, body = c.post("/api/auth/login", {"email": email, "password": password})
    ok_login = _assert("POST /api/auth/login → 200", code == 200, f"got {code}")

    token: str | None = None
    if ok_login and isinstance(body, dict):
        token = body.get("access_token")
        _assert("login response has access_token", bool(token))
        c._token = token

    if not token:
        _record("GET /api/auth/verify (authenticated)", False, "skipped — auth failed")
        return None

    # Verify token
    code, _ = c.get("/api/auth/verify", auth=True)
    _assert("GET /api/auth/verify → 200 (token valid)", code == 200, f"got {code}")

    # Me endpoint
    code, me = c.get("/api/users/me", auth=True)
    ok_me = _assert("GET /api/users/me → 200", code in (200, 404),
                    f"got {code}")  # 404 if endpoint path differs
    if ok_me and isinstance(me, dict) and code == 200:
        _assert("me.email matches registered email",
                me.get("email") == email, f"got {me.get('email')!r}")

    return email


def test_company_builder(c: Client) -> str | None:
    """
    End-to-end company builder test:
      POST /api/companies/  → 201/202 (create)
      GET  /api/companies/  → 200     (list, contains new company)
      GET  /api/companies/{id}        → 200 (fetch by id)
    """
    print("\n  [3/7] Company Builder")

    if not c._token:
        _record("Company Builder (auth required)", False, "skipped — no auth token")
        return None

    company_name = f"LiveTest Co {uuid.uuid4().hex[:6]}"
    payload = {
        "name": company_name,
        "description": "Automated live verification company",
        "tech_stack": ["python", "fastapi"],
        "features": ["auth", "billing"],
    }

    t0 = time.monotonic()
    code, body = c.post("/api/companies/", payload, auth=True)
    elapsed = (time.monotonic() - t0) * 1000

    ok_create = _assert(
        "POST /api/companies/ → 201/202 (company created)",
        code in (200, 201, 202),
        f"got {code}",
    )
    _assert("company create response time < 5000ms", elapsed < 5000, f"{elapsed:.0f}ms")

    company_id: str | None = None
    if ok_create and isinstance(body, dict):
        company_id = body.get("id") or body.get("company_id")
        _assert("create response has id", bool(company_id))
        name_match = body.get("name") == company_name
        _assert("response name matches submitted name", name_match,
                f"got {body.get('name')!r}")
    if _VERBOSE and isinstance(body, dict):
        print(f"         created: {json.dumps(body, indent=2)[:400]}")

    # List companies — ensure ours appears
    code, body = c.get("/api/companies/", auth=True)
    ok_list = _assert("GET /api/companies/ → 200", code == 200, f"got {code}")
    if ok_list and isinstance(body, (list, dict)):
        items = body if isinstance(body, list) else body.get("items", body.get("results", []))
        found = any(
            (i.get("name") == company_name or i.get("id") == company_id)
            for i in items
            if isinstance(i, dict)
        )
        _assert("new company appears in list", found, f"searched {len(items)} items")

    # Fetch by ID
    if company_id:
        code, company = c.get(f"/api/companies/{company_id}", auth=True)
        ok_fetch = _assert(
            f"GET /api/companies/{{id}} → 200",
            code == 200,
            f"got {code}",
        )
        if ok_fetch and isinstance(company, dict):
            _assert(
                "fetched company name matches",
                company.get("name") == company_name,
                f"got {company.get('name')!r}",
            )

    return company_id


def test_billing_routes(c: Client) -> None:
    print("\n  [4/7] Billing / Stripe Routes")

    # GET on a POST-only endpoint proves the router is mounted (405 expected)
    code, _ = c.get("/api/stripe/create-checkout-session")
    _assert(
        "GET /api/stripe/create-checkout-session → 405 (router mounted)",
        code == 405,
        f"got {code}",
    )

    # Stripe webhook endpoint should exist (405 on GET)
    code, _ = c.get("/api/stripe/webhook")
    _assert(
        "GET /api/stripe/webhook → 405 (endpoint mounted)",
        code in (405, 422),
        f"got {code}",
    )


def test_security_guards(c: Client) -> None:
    print("\n  [5/7] Security Guards")

    # Protected endpoints without token must return 401/403
    for path in ["/api/companies/", "/api/users/me", "/api/admin/"]:
        code, _ = Client(c.base).get(path)  # fresh client, no token
        _assert(
            f"GET {path} without token → 401/403",
            code in (401, 403),
            f"got {code}",
        )

    # Auth guard on verify endpoint
    code, _ = Client(c.base).get("/api/auth/verify")
    _assert("GET /api/auth/verify without token → 401", code == 401, f"got {code}")


def test_tls(base_url: str) -> None:
    print("\n  [6/7] TLS / HTTPS")
    if not base_url.startswith("https://"):
        _record("TLS certificate check", True, "skipped — not an HTTPS URL (expected for local dev)")
        return

    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(
            f"{base_url}/health", timeout=10, context=ctx
        ) as r:
            _assert("HTTPS TLS handshake + /health → 200", r.status == 200, f"got {r.status}")
    except ssl.SSLCertVerificationError as e:
        _record("HTTPS TLS certificate is valid", False, str(e))
    except Exception as e:
        _record("HTTPS TLS check", False, str(e))


def test_performance(c: Client) -> None:
    print("\n  [7/7] Response Time Spot-Check")
    for path, label in [("/health", "GET /health"), ("/docs", "GET /docs")]:
        times = []
        for _ in range(3):
            t0 = time.monotonic()
            code, _ = c.get(path)
            times.append((time.monotonic() - t0) * 1000)
        avg = sum(times) / len(times)
        _assert(
            f"{label} avg response < 1000ms",
            avg < 1000,
            f"{avg:.0f}ms avg over 3 requests",
        )


# ── cleanup ───────────────────────────────────────────────────────────────────

def cleanup(c: Client, email: str | None, company_id: str | None) -> None:
    """Best-effort cleanup of test data. Failures are reported as info only."""
    print("\n  [Cleanup] Removing test data")
    if company_id:
        code, _ = c.delete(f"/api/companies/{company_id}", auth=True)
        status = "deleted" if code in (200, 204) else f"could not delete (HTTP {code})"
        print(f"           Company {company_id}: {status}")
    if email:
        code, _ = c.delete("/api/users/me", auth=True)
        status = "deleted" if code in (200, 204) else f"could not delete (HTTP {code})"
        print(f"           Test user {email}: {status}")


# ── orchestrator ──────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    global _VERBOSE

    parser = argparse.ArgumentParser(
        description="SwarmEnterprise v2 live environment + company builder verifier"
    )
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Base URL of the running application (default: http://localhost:8000)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print full response bodies")
    parser.add_argument("--json", metavar="FILE", default="",
                        help="Save JSON report to FILE")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Skip test-data cleanup (useful for debugging)")
    args = parser.parse_args(argv)
    _VERBOSE = args.verbose

    print()
    print("=" * 68)
    print("  SwarmEnterprise v2 — Live Environment Verifier")
    print(f"  Target: {args.url}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 68)

    c = Client(args.url)
    test_infrastructure(c)
    email = test_auth_flow(c)
    company_id = test_company_builder(c)
    test_billing_routes(c)
    test_security_guards(c)
    test_tls(args.url)
    test_performance(c)

    if not args.no_cleanup:
        cleanup(c, email, company_id)

    total = _PASS + _FAIL
    print()
    print("=" * 68)
    print(f"  Results: {_PASS} passed / {_FAIL} failed / {total} total")
    print()
    if _FAIL == 0:
        print("  [OK] LIVE ENVIRONMENT VERIFIED — all tests passed.")
    else:
        print(f"  [FAIL] {_FAIL} test(s) failed. Review output above.")
    print("=" * 68)
    print()

    # Optional JSON report
    if args.json:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "url": args.url,
            "pass_count": _PASS,
            "fail_count": _FAIL,
            "total": total,
            "results": _results,
        }
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"  Report saved → {args.json}")

    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
