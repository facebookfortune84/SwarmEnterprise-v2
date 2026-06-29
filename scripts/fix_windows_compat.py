#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/fix_windows_compat.py
Idempotent patcher — applies Windows-compatibility fixes to the project.

Patches applied (each is idempotent: running twice = same as running once):
  1. alembic/env.py  — insert sys.path fix before `from backend.db.models`
  2. Makefile        — replace bare `| tr '[:upper:]' '[:lower:]'` with Python
  3. Makefile        — replace bare `if [ -f package.json ]` with cross-platform block
  4. Makefile        — add `check-docker` target if not present
  5. Makefile        — add `venv` target if not present
  6. scripts/run_alembic.py — create if not present

Run:
    python scripts/fix_windows_compat.py
"""

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent

ALEMBIC_ENV = PROJECT_ROOT / "alembic" / "env.py"
MAKEFILE = PROJECT_ROOT / "Makefile"
RUN_ALEMBIC = PROJECT_ROOT / "scripts" / "run_alembic.py"

# ---------------------------------------------------------------------------
# Helper: read / write UTF-8
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------
patches_applied = 0
patches_skipped = 0


def _applied(name: str) -> None:
    global patches_applied
    patches_applied += 1
    print(f"  [PATCHED] {name}")


def _skipped(name: str) -> None:
    global patches_skipped
    patches_skipped += 1
    print(f"  [ALREADY OK] {name}")


# ===========================================================================
# Patch 1 — alembic/env.py: sys.path.insert fix
# ===========================================================================

_ALEMBIC_MARKER = "sys.path.insert(0, _PROJECT_ROOT_STR)"
_ALEMBIC_PATCH = """\
import sys

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `from backend.db.models`
# works whether Alembic is invoked from the repo root, a subdirectory, or
# inside a Docker container where PYTHONPATH may not be set.
# ---------------------------------------------------------------------------
_ALEMBIC_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT_STR = os.path.abspath(os.path.join(_ALEMBIC_DIR, ".."))
if _PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT_STR)

"""


def patch_alembic_env() -> None:
    if not ALEMBIC_ENV.exists():
        print(f"  [SKIP] {ALEMBIC_ENV} not found")
        return

    content = _read(ALEMBIC_ENV)

    # Already patched?
    if _ALEMBIC_MARKER in content:
        _skipped("alembic/env.py — sys.path fix")
        return

    # Insert after `import os` line (first occurrence)
    if "import os\n" in content:
        content = content.replace("import os\n", "import os\n" + _ALEMBIC_PATCH, 1)
    elif "import os" in content:
        # Edge case: no trailing newline on that line
        content = content.replace("import os", "import os\n" + _ALEMBIC_PATCH, 1)
    else:
        # Prepend at top after docstring
        content = _ALEMBIC_PATCH + content

    _write(ALEMBIC_ENV, content)
    _applied("alembic/env.py — sys.path fix")


# ===========================================================================
# Patch 2 — Makefile: replace bare `| tr '[:upper:]' '[:lower:]'`
# ===========================================================================
#
# Original:
#   FULL_IMAGE := $(REGISTRY)/$(shell echo "$(IMAGE_NAME)" | tr '[:upper:]' '[:lower:]')
# Replacement:
#   FULL_IMAGE := $(REGISTRY)/$(shell python -c "print('$(IMAGE_NAME)'.lower())" 2>/dev/null || echo "$(IMAGE_NAME)")
#
_TR_PATTERN = re.compile(
    r'\$\(shell\s+echo\s+"[^"]*"\s*\|\s*tr\s+\'[^\']+\'\s+\'[^\']+\'\)',
    re.IGNORECASE,
)
_TR_REPLACEMENT = (
    r"$(shell python -c \"print('$(IMAGE_NAME)'.lower())\" 2>/dev/null || echo \"$(IMAGE_NAME)\")"
)


def patch_makefile_tr() -> None:
    if not MAKEFILE.exists():
        print("  [SKIP] Makefile not found")
        return

    content = _read(MAKEFILE)

    # Already patched?
    if "| tr " not in content:
        _skipped("Makefile — tr replacement")
        return

    # Replace the specific FULL_IMAGE line
    new_content = re.sub(
        r"(FULL_IMAGE\s*:=\s*\$\(REGISTRY\)/)\$\(shell\s+echo\s+\"[^\"]*\"\s*\|\s*tr[^\)]+\)",
        r"\1$(shell python -c \"print('$(IMAGE_NAME)'.lower())\" 2>/dev/null || echo \"$(IMAGE_NAME)\")",
        content,
    )

    if new_content == content:
        # Generic fallback: replace any remaining `| tr 'X' 'Y'` pipe
        new_content = re.sub(r"\|\s*tr\s+'[^']+'\s+'[^']+'", "", content)

    if new_content != content:
        _write(MAKEFILE, new_content)
        _applied("Makefile — tr replacement")
    else:
        _skipped("Makefile — tr replacement (nothing matched)")


# ===========================================================================
# Patch 3 — Makefile: replace bare `if [ -f package.json ]` in install
# ===========================================================================
_BARE_IF_F = "if [ -f package.json ]"
_CROSS_PLATFORM_NPM = """\
ifeq ($(OS),Windows_NT)
\t@powershell -NoProfile -Command \\
\t  "if (Test-Path 'package.json') { npm ci } else { Write-Host '[install] No package.json, skipping npm.' }"
else
\t@if [ -f package.json ]; then npm ci; else echo "[install] No package.json, skipping npm."; fi
endif"""


def patch_makefile_if_f() -> None:
    if not MAKEFILE.exists():
        return

    content = _read(MAKEFILE)

    # If there's already an ifeq(OS,Windows_NT) block guarding npm, we're done.
    # Detect by checking if the bare conditional only appears inside an else/endif block.
    if _BARE_IF_F not in content:
        _skipped("Makefile — if [ -f package.json ] replacement (not present)")
        return

    # Check whether the bare @if [ -f is already inside an ifeq guard
    lines = content.splitlines()
    in_win_block = False
    bare_outside_guard = False
    for ln in lines:
        stripped = ln.strip()
        if "ifeq ($(OS),Windows_NT)" in ln or "ifeq($(OS),Windows_NT)" in ln:
            in_win_block = True
        if stripped == "endif":
            in_win_block = False
        if re.search(r"@if \[ -f package\.json \]", ln) and not in_win_block:
            bare_outside_guard = True
            break

    if not bare_outside_guard:
        _skipped("Makefile — if [ -f package.json ] already inside ifeq guard")
        return

    # Replace only bare occurrences (outside any ifeq Windows block)
    new_content = re.sub(
        r"[ \t]*@if \[ -f package\.json \];[^\n]*\n?",
        _CROSS_PLATFORM_NPM + "\n",
        content,
    )

    if new_content != content:
        _write(MAKEFILE, new_content)
        _applied("Makefile — if [ -f package.json ] replacement")
    else:
        _skipped("Makefile — if [ -f package.json ] (nothing to replace)")


# ===========================================================================
# Patch 4 — Makefile: add `check-docker` target if not present
# ===========================================================================
_CHECK_DOCKER_MARKER = "check-docker:"
_CHECK_DOCKER_TARGET = """
# ─────────────────────────────────────────────────────────────────────────────
# CHECK-DOCKER — preflight guard for all Docker-dependent targets
# ─────────────────────────────────────────────────────────────────────────────

## Verify Docker Desktop / daemon is running; exits 1 with a clear message if not
check-docker:
ifeq ($(OS),Windows_NT)
\t@powershell -NoProfile -Command \\
\t  "docker info 2>&1 | Out-Null; \\
\t   if ($$LASTEXITCODE -ne 0) { \\
\t     Write-Error 'ERROR: Docker is not running. Start Docker Desktop and try again.'; \\
\t     exit 1 \\
\t   } else { \\
\t     Write-Host '[check-docker] Docker is running.' \\
\t   }"
else
\t@docker info >/dev/null 2>&1 || \\
\t  (echo "ERROR: Docker is not running. Start Docker Desktop / dockerd and try again." && exit 1)
\t@echo "[check-docker] Docker is running."
endif
"""


def patch_makefile_check_docker() -> None:
    if not MAKEFILE.exists():
        return

    content = _read(MAKEFILE)

    if _CHECK_DOCKER_MARKER in content:
        _skipped("Makefile — check-docker target")
        return

    # Add check-docker to .PHONY if it exists
    content = re.sub(
        r"(\.PHONY:[^\n]*\\\n[^\n]*)",
        lambda m: m.group(0) + " check-docker",
        content,
        count=1,
    )

    # Append target at end
    content = content.rstrip("\n") + "\n" + _CHECK_DOCKER_TARGET + "\n"
    _write(MAKEFILE, content)
    _applied("Makefile — check-docker target")


# ===========================================================================
# Patch 5 — Makefile: add `venv` target if not present
# ===========================================================================
_VENV_MARKER = "\nvenv:"
_VENV_TARGET = """
# ─────────────────────────────────────────────────────────────────────────────
# VENV — create isolated virtual environment
# ─────────────────────────────────────────────────────────────────────────────

## Create .venv virtual environment if it does not already exist
venv:
ifeq ($(OS),Windows_NT)
\t@powershell -NoProfile -Command \\
\t  "if (-Not (Test-Path '.venv\\\\Scripts\\\\python.exe')) { \\
\t    Write-Host '[venv] Creating .venv ...'; \\
\t    python -m venv .venv; \\
\t    Write-Host '[venv] Done.' \\
\t  } else { \\
\t    Write-Host '[venv] .venv already exists, skipping.' \\
\t  }"
else
\t@if [ ! -f .venv/bin/python ]; then \\
\t  echo "[venv] Creating .venv ..."; \\
\t  python3 -m venv .venv; \\
\t  echo "[venv] Done."; \\
\telse \\
\t  echo "[venv] .venv already exists, skipping."; \\
\tfi
endif
"""


def patch_makefile_venv() -> None:
    if not MAKEFILE.exists():
        return

    content = _read(MAKEFILE)

    if _VENV_MARKER in content or "\nvenv:\n" in content:
        _skipped("Makefile — venv target")
        return

    content = content.rstrip("\n") + "\n" + _VENV_TARGET + "\n"
    _write(MAKEFILE, content)
    _applied("Makefile — venv target")


# ===========================================================================
# Patch 6 — scripts/run_alembic.py: create if not present
# ===========================================================================
_RUN_ALEMBIC_CONTENT = '''\
#!/usr/bin/env python3
"""
scripts/run_alembic.py
Cross-platform Alembic runner.

Ensures PYTHONPATH includes the project root before delegating to
`alembic` so that `from backend.db.models import Base` always resolves,
regardless of which directory or shell the user invokes this from.

Usage:
    python scripts/run_alembic.py upgrade head
    python scripts/run_alembic.py downgrade -1
    python scripts/run_alembic.py revision --autogenerate -m "add table"
"""

import os
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent

env = os.environ.copy()
existing_pp = env.get("PYTHONPATH", "")
sep = ";" if sys.platform == "win32" else ":"
if str(_PROJECT_ROOT) not in existing_pp.split(sep):
    env["PYTHONPATH"] = str(_PROJECT_ROOT) + (sep + existing_pp if existing_pp else "")

cmd = [sys.executable, "-m", "alembic"] + sys.argv[1:]
print(f"[run_alembic] {chr(32).join(cmd)}")
print(f"[run_alembic] PYTHONPATH={env[\'PYTHONPATH\']}")
print(f"[run_alembic] cwd={_PROJECT_ROOT}")

result = subprocess.run(cmd, env=env, cwd=str(_PROJECT_ROOT))
sys.exit(result.returncode)
'''


def patch_run_alembic() -> None:
    if RUN_ALEMBIC.exists():
        _skipped("scripts/run_alembic.py — already exists")
        return

    _write(RUN_ALEMBIC, _RUN_ALEMBIC_CONTENT)
    _applied("scripts/run_alembic.py — created")


# ===========================================================================
# Main
# ===========================================================================

def main() -> int:
    print()
    print("=" * 60)
    print("  SwarmEnterprise v2 — Windows Compatibility Patcher")
    print("=" * 60)
    print()

    patch_alembic_env()
    patch_makefile_tr()
    patch_makefile_if_f()
    patch_makefile_check_docker()
    patch_makefile_venv()
    patch_run_alembic()

    print()
    print("=" * 60)
    print(f"  Summary: {patches_applied} patch(es) applied, "
          f"{patches_skipped} already in place.")
    print("=" * 60)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
