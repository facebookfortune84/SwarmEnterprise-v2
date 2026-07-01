#!/usr/bin/env python3
"""
scripts/wait_postgres.py
Poll 'docker compose exec postgres pg_isready' until Postgres accepts
connections, then exit 0.  Exits 1 if the timeout expires.

Why this script instead of a bash loop:
  - Works on Windows (cmd.exe / PowerShell) without bash.
  - Works on Linux/macOS identically.
  - Reads POSTGRES_USER and COMPOSE_FILE from environment or uses sensible
    defaults matching docker-compose.yml.

Usage (called automatically by `make launch` and `make full-launch`):
    python scripts/wait_postgres.py

Environment variables honoured:
    POSTGRES_USER   — pg_isready -U <user>   (default: swarm)
    COMPOSE_FILE    — compose file path       (default: docker-compose.yml)
    PG_WAIT_TIMEOUT — total seconds to wait  (default: 120)
    PG_WAIT_INTERVAL— seconds between polls  (default: 2)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PG_USER      = os.getenv("POSTGRES_USER", "swarm")
COMPOSE_FILE = os.getenv("COMPOSE_FILE",  "docker-compose.yml")
TIMEOUT      = int(os.getenv("PG_WAIT_TIMEOUT",   "120"))
INTERVAL     = int(os.getenv("PG_WAIT_INTERVAL",  "2"))


def _pg_isready() -> bool:
    """Return True if postgres container responds to pg_isready."""
    result = subprocess.run(
        [
            "docker", "compose",
            "-f", COMPOSE_FILE,
            "exec", "-T", "postgres",
            "pg_isready", "-U", PG_USER,
        ],
        capture_output=True,
        cwd=str(ROOT),
    )
    return result.returncode == 0


def main() -> int:
    print(f"[wait_postgres] Waiting for PostgreSQL (user={PG_USER}, "
          f"timeout={TIMEOUT}s, interval={INTERVAL}s) ...")

    deadline = time.time() + TIMEOUT
    attempt  = 0

    while time.time() < deadline:
        attempt += 1
        if _pg_isready():
            print(f"[wait_postgres] PostgreSQL is ready (attempt {attempt})")
            return 0
        remaining = int(deadline - time.time())
        print(f"[wait_postgres]   attempt {attempt} — not ready yet "
              f"({remaining}s remaining) ...")
        time.sleep(INTERVAL)

    print(
        f"[wait_postgres] ERROR: PostgreSQL did not become ready within {TIMEOUT}s.\n"
        f"  Check container logs:  docker compose logs postgres\n"
        f"  Check container state: docker compose ps",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
