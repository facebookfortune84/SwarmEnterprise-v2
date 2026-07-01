#!/usr/bin/env python3
"""
scripts/run_alembic.py
Cross-platform Alembic runner.

Ensures PYTHONPATH includes the project root before delegating to
`alembic` so that `from backend.db.models import Base` always resolves,
regardless of which directory or shell the user invokes this from.

Usage (replaces bare `alembic` calls):
    python scripts/run_alembic.py upgrade head
    python scripts/run_alembic.py downgrade -1
    python scripts/run_alembic.py revision --autogenerate -m "add table"
    python scripts/run_alembic.py current
    python scripts/run_alembic.py history --verbose

NOTE — Docker deployments
    When DATABASE_URL points to a Docker service name (e.g. "postgres") the
    database is only reachable from *inside* the Docker network.
    Running this script from the host venv will fail with a DNS error.
    Use the Makefile targets instead:
        make migrate          # runs inside the container
        make rollback         # runs inside the container
    Or directly:
        docker compose exec backend alembic upgrade head
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Resolve project root (two levels up from this script in scripts/)
# ---------------------------------------------------------------------------
_SCRIPT_DIR   = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

# ---------------------------------------------------------------------------
# Guard: detect Docker-internal hostnames before attempting a connection.
#
# If DATABASE_URL contains a Docker service name as the hostname (e.g.
# "postgres", "db", "database") or resolves to localhost but port 5432 is
# not reachable from the host, print an instructional message and exit 0
# (soft exit — the Makefile should not abort on a pre-launch check because
# of this; the actual migration will be run inside Docker).
# ---------------------------------------------------------------------------
_DOCKER_SERVICE_NAMES = {"postgres", "db", "database", "pgdb", "postgresql"}
_SOFT_EXIT_KEYWORDS   = (
    "no such host",
    "name or service not known",
    "could not translate",
    "getaddrinfo failed",
    "nodename nor servname provided",
    "connection refused",
)

_DB_URL = os.getenv("DATABASE_URL", "")

def _is_docker_hostname(url: str) -> bool:
    """Return True if the DB URL uses a Docker-internal service hostname."""
    if not url:
        return False
    try:
        parsed = urlparse(url.replace("+asyncpg", "").replace("+psycopg2", ""))
        host = (parsed.hostname or "").lower()
        return host in _DOCKER_SERVICE_NAMES
    except Exception:
        return False


def _print_docker_hint() -> None:
    print(
        "\n[run_alembic] INFO: DATABASE_URL points to a Docker service hostname.\n"
        "  Alembic cannot connect to the database from the host machine because\n"
        "  the hostname is only reachable inside the Docker network.\n"
        "\n"
        "  Run migrations inside the container instead:\n"
        "    make migrate\n"
        "  or:\n"
        "    docker compose exec backend alembic upgrade head\n",
        file=sys.stderr,
    )


if _is_docker_hostname(_DB_URL):
    _print_docker_hint()
    # Exit 0 — soft warning.  The Makefile will not abort; the actual
    # migration is handled by 'docker compose exec backend alembic ...'
    sys.exit(0)

# ---------------------------------------------------------------------------
# Inject project root into PYTHONPATH so backend package is importable
# ---------------------------------------------------------------------------
env = os.environ.copy()
existing_pp = env.get("PYTHONPATH", "")
sep = ";" if sys.platform == "win32" else ":"
if str(_PROJECT_ROOT) not in existing_pp.split(sep):
    env["PYTHONPATH"] = str(_PROJECT_ROOT) + (sep + existing_pp if existing_pp else "")

# ---------------------------------------------------------------------------
# Run `python -m alembic <args>` using the *same* Python interpreter that
# is running this script (i.e., the .venv Python when invoked via Makefile).
# ---------------------------------------------------------------------------
cmd = [sys.executable, "-m", "alembic"] + sys.argv[1:]

print(f"[run_alembic] {' '.join(cmd)}")
print(f"[run_alembic] PYTHONPATH={env['PYTHONPATH']}")
print(f"[run_alembic] cwd={_PROJECT_ROOT}")

# Run capturing output so we can inspect it for connection errors before
# deciding whether to forward the exit code or issue a soft-exit hint.
result = subprocess.run(
    cmd, env=env, cwd=str(_PROJECT_ROOT),
    capture_output=True, text=True,
)

combined = (result.stdout + result.stderr).lower()

if result.returncode != 0 and any(kw in combined for kw in _SOFT_EXIT_KEYWORDS):
    # Print stdout normally (usually empty for connection errors)
    if result.stdout.strip():
        print(result.stdout, end="")
    _print_docker_hint()
    sys.exit(0)   # soft exit — connection error due to host isolation

# Normal exit: forward output and return code.
if result.stdout:
    print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)
sys.exit(result.returncode)
