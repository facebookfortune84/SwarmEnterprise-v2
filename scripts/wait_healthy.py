#!/usr/bin/env python3
"""
scripts/wait_healthy.py
Poll an HTTP endpoint until it responds 2xx, then exit 0.
Exits 1 if the timeout expires without a healthy response.

Usage:
    python scripts/wait_healthy.py <port> [timeout_seconds] [path]

Examples:
    python scripts/wait_healthy.py 8000 30
    python scripts/wait_healthy.py 3001 30 /api/heartbeat
"""

import sys
import time
import urllib.error
import urllib.request


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    path = sys.argv[3] if len(sys.argv) > 3 else "/health"
    url = f"http://localhost:{port}{path}"

    print(f"[wait_healthy] Waiting up to {timeout}s for {url} ...")
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status < 400:
                    print(f"[wait_healthy] OK after {attempt} attempt(s) (HTTP {r.status})")
                    return 0
        except Exception:
            pass
        time.sleep(2)

    print(
        f"[wait_healthy] TIMEOUT: {url} did not respond within {timeout}s.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
