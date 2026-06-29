#!/usr/bin/env python3
"""
scripts/run_health_check.py
Cross-platform replacement for the bash health-check recipe in the Makefile.
Usage: python scripts/run_health_check.py [backend_port] [analytics_port]
"""
import json
import sys
import urllib.error
import urllib.request

BACKEND_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
ANALYTICS_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 3001


def _get(url: str, timeout: int = 5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return None, str(exc)


print()
print("  SwarmOS Health Check")
print("  " + "-" * 62)

# Backend
backend_url = f"http://localhost:{BACKEND_PORT}/health"
print(f"  Checking {backend_url} ...")
status, body = _get(backend_url)
if status and status < 400:
    try:
        d = json.loads(body)
        ver = d.get("version", "?")
        db = d.get("checks", {}).get("db", "?")
        redis = d.get("checks", {}).get("redis", "?")
        print(f"  [OK] Backend:   ONLINE  version={ver} | db={db} | redis={redis}")
    except Exception:
        print(f"  [OK] Backend:   ONLINE  ({body[:80]})")
else:
    print(f"  [FAIL] Backend:   UNREACHABLE — {body[:120]}")
    print("         Is it running?  Try: make start")

# Analytics
analytics_url = f"http://localhost:{ANALYTICS_PORT}/api/heartbeat"
a_status, _ = _get(analytics_url, timeout=3)
if a_status and a_status < 400:
    print(f"  [OK] Analytics: http://localhost:{ANALYTICS_PORT}")
else:
    print(f"  [WARN] Analytics: offline (start with: make docker-up-analytics)")

print()
