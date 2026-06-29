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
"""

import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root (two levels up from this script in scripts/)
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

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

result = subprocess.run(cmd, env=env, cwd=str(_PROJECT_ROOT))
sys.exit(result.returncode)
