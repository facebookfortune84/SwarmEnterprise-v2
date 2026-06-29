#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/test_launch_readiness.py
Standalone stdlib-only launch-readiness test suite.

Usage:
    python scripts/test_launch_readiness.py

Exit codes:
    0 — all checks passed (WARNs are acceptable)
    1 — one or more checks FAILED

Prints a formatted table of results.  No pytest required.
"""

import importlib.util
import os
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent

# On Windows .venv\Scripts\python.exe; on Linux/macOS .venv/bin/python
if sys.platform == "win32":
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# ---------------------------------------------------------------------------
# Required environment variables
# ---------------------------------------------------------------------------
REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
    "POSTGRES_DB",
    "REDIS_URL",
    "STRIPE_API_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PUBLISHABLE_KEY",
    "SMTP_USER",
    "SMTP_PASS",
    "SMTP_SERVER",
    "SMTP_PORT",
    "JWT_SECRET_KEY",
    "SECRET_KEY",
]

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"

Results: List[Tuple[str, str, str]] = []  # (name, status, reason)


def record(name: str, status: str, reason: str = "") -> None:
    Results.append((name, status, reason))
    sym = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}[status]
    print(f"  {sym}  {name}" + (f"  --  {reason}" if reason else ""))


# ---------------------------------------------------------------------------
# Helper: load .env into os.environ (simple parser, no external deps)
# ---------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


# ---------------------------------------------------------------------------
# Helper: TCP reachability check
# ---------------------------------------------------------------------------
def _tcp_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Helper: parse host/port from a database URL
# ---------------------------------------------------------------------------
def _parse_db_host_port(url: str) -> Tuple[str, int]:
    """Return (host, port) from a postgres/sqlite URL; returns ('', 0) on failure."""
    try:
        # postgresql+asyncpg://user:pass@host:5432/dbname
        m = re.search(r"@([^:/]+):(\d+)/", url)
        if m:
            return m.group(1), int(m.group(2))
        # postgresql://user:pass@host/dbname  (default port 5432)
        m = re.search(r"@([^/]+)/", url)
        if m:
            return m.group(1), 5432
    except Exception:
        pass
    return "", 0


# ---------------------------------------------------------------------------
# Helper: run a subprocess and return (returncode, stdout, stderr)
# ---------------------------------------------------------------------------
def _run(cmd: List[str], cwd: str = None, env: dict = None,
         timeout: int = 60) -> Tuple[int, str, str]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(PROJECT_ROOT),
            env=env,
            timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError as exc:
        return -1, "", str(exc)


# ===========================================================================
# Check 1 — .env file exists and required variables are non-empty
# ===========================================================================
def check_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        record(".env file exists", FAIL, f"{env_path} not found — run: cp .env.example .env")
        return
    record(".env file exists", PASS)

    # Load into current process so subsequent checks benefit
    _load_dotenv(env_path)

    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v, "").strip()]
    if missing:
        record(
            ".env required variables",
            FAIL,
            f"Missing or empty: {', '.join(missing)}",
        )
    else:
        record(".env required variables", PASS, f"All {len(REQUIRED_ENV_VARS)} vars present")


# ===========================================================================
# Check 2 — .venv exists and Python is executable
# ===========================================================================
def check_venv() -> None:
    if not VENV_PYTHON.exists():
        record(
            ".venv Python executable",
            FAIL,
            f"{VENV_PYTHON} not found — run: make venv && make install",
        )
        return
    rc, out, _ = _run([str(VENV_PYTHON), "--version"])
    if rc == 0:
        record(".venv Python executable", PASS, out.strip())
    else:
        record(".venv Python executable", FAIL, "python --version failed in .venv")


# ===========================================================================
# Check 3 — requirements.txt packages importable inside .venv
# ===========================================================================
def check_requirements_installed() -> None:
    if not VENV_PYTHON.exists():
        record("requirements.txt installed in .venv", SKIP, ".venv not found")
        return

    req_path = PROJECT_ROOT / "requirements.txt"
    if not req_path.exists():
        record("requirements.txt installed in .venv", SKIP, "requirements.txt not found")
        return

    rc, out, err = _run(
        [
            str(VENV_PYTHON),
            "-c",
            "import pkg_resources; pkg_resources.require(open('requirements.txt').readlines())",
        ],
        timeout=30,
    )
    if rc == 0:
        record("requirements.txt installed in .venv", PASS)
    else:
        # Extract the first missing package from the error
        hint = (err or out).splitlines()[0][:120] if (err or out) else "unknown error"
        record("requirements.txt installed in .venv", FAIL, hint)


# ===========================================================================
# Check 4 — alembic/env.py contains sys.path fix
# ===========================================================================
def check_alembic_env_patched() -> None:
    path = PROJECT_ROOT / "alembic" / "env.py"
    if not path.exists():
        record("alembic/env.py sys.path fix", SKIP, "file not found")
        return
    content = path.read_text(encoding="utf-8")
    if "sys.path.insert" in content and "_PROJECT_ROOT_STR" in content:
        record("alembic/env.py sys.path fix", PASS)
    else:
        record(
            "alembic/env.py sys.path fix",
            FAIL,
            "sys.path.insert(_PROJECT_ROOT_STR) not found — run: python scripts/fix_windows_compat.py",
        )


# ===========================================================================
# Check 5 — alembic upgrade head (skip if DB unreachable)
# ===========================================================================
def check_alembic_migrate() -> None:
    if not VENV_PYTHON.exists():
        record("alembic upgrade head", SKIP, ".venv not found")
        return

    db_url = os.environ.get("DATABASE_URL", "")
    if "postgresql" in db_url or "postgres" in db_url:
        host, port = _parse_db_host_port(db_url)
        if host and port and not _tcp_reachable(host, port):
            record(
                "alembic upgrade head",
                SKIP,
                f"Database unreachable at {host}:{port} — skipping migration check",
            )
            return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    rc, out, err = _run(
        [str(VENV_PYTHON), str(PROJECT_ROOT / "scripts" / "run_alembic.py"), "upgrade", "head"],
        env=env,
        timeout=60,
    )
    if rc == 0:
        record("alembic upgrade head", PASS)
    else:
        hint = (err or out).splitlines()[-1][:120] if (err or out) else "non-zero exit"
        record("alembic upgrade head", FAIL, hint)


# ===========================================================================
# Check 6 — backend/db/models.py importable
# ===========================================================================
def check_models_importable() -> None:
    models_path = PROJECT_ROOT / "backend" / "db" / "models.py"
    if not models_path.exists():
        record("backend/db/models.py importable", FAIL, "file not found")
        return

    if not VENV_PYTHON.exists():
        record("backend/db/models.py importable", SKIP, ".venv not found")
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    rc, out, err = _run(
        [
            str(VENV_PYTHON),
            "-c",
            "import sys; sys.path.insert(0, '.'); from backend.db.models import Base; print('Base tables:', len(Base.metadata.tables))",
        ],
        env=env,
        timeout=20,
    )
    if rc == 0:
        record("backend/db/models.py importable", PASS, out.strip())
    else:
        hint = (err or out).splitlines()[0][:120] if (err or out) else "import failed"
        record("backend/db/models.py importable", FAIL, hint)


# ===========================================================================
# Check 7 — backend/main.py FastAPI app importable
# ===========================================================================
def check_app_importable() -> None:
    main_path = PROJECT_ROOT / "backend" / "main.py"
    if not main_path.exists():
        record("backend/main.py app importable", FAIL, "file not found")
        return

    if not VENV_PYTHON.exists():
        record("backend/main.py app importable", SKIP, ".venv not found")
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    # Minimal stubs so startup doesn't fail on missing secrets
    for var, val in [
        ("JWT_SECRET_KEY", env.get("JWT_SECRET_KEY", "ci-test-key-00000000000000000000000000000000000000000000000000000000")),
        ("SECRET_KEY",     env.get("SECRET_KEY",     "ci-test-key-11111111111111111111111111111111111111111111111111111111")),
        ("DATABASE_URL",   env.get("DATABASE_URL",   "sqlite:///./test_import.db")),
        ("REDIS_URL",      env.get("REDIS_URL",      "redis://localhost:6379/0")),
        ("STRIPE_API_KEY", env.get("STRIPE_API_KEY", "sk_test_placeholder")),
        ("STRIPE_WEBHOOK_SECRET", env.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")),
        ("PYTHONPATH",     str(PROJECT_ROOT)),
        ("OTEL_SDK_DISABLED", "true"),
        ("CREWAI_DISABLE_TELEMETRY", "true"),
    ]:
        env[var] = val

    rc, out, err = _run(
        [
            str(VENV_PYTHON),
            "-c",
            "from backend.main import app; print('app type:', type(app).__name__)",
        ],
        env=env,
        timeout=30,
    )
    if rc == 0:
        record("backend/main.py app importable", PASS, out.strip())
    else:
        hint = (err or out).splitlines()[0][:120] if (err or out) else "import failed"
        record("backend/main.py app importable", FAIL, hint)


# ===========================================================================
# Check 8 — frontend static assets referenced in index.html exist on disk
# ===========================================================================
def check_frontend_assets() -> None:
    index_html = PROJECT_ROOT / "frontend" / "public" / "index.html"
    if not index_html.exists():
        record("frontend static assets", SKIP, "frontend/public/index.html not found")
        return

    content = index_html.read_text(encoding="utf-8")
    # Find src="..." and href="..." values
    refs = re.findall(r'(?:src|href)=["\']([^"\'#?]+)["\']', content)

    missing = []
    for ref in refs:
        # Skip external URLs and anchors
        if ref.startswith(("http://", "https://", "//", "mailto:")):
            continue
        # Normalise: /dashboard/foo.js -> frontend/public/foo.js
        norm = ref.lstrip("/")
        if norm.startswith("dashboard/"):
            norm = norm[len("dashboard/"):]
        elif norm.startswith("corp/"):
            norm = norm[len("corp/"):]
        candidate = PROJECT_ROOT / "frontend" / "public" / norm
        if not candidate.exists():
            missing.append(ref)

    if missing:
        record(
            "frontend static assets",
            FAIL,
            f"Missing: {', '.join(missing[:5])}" + (" ..." if len(missing) > 5 else ""),
        )
    else:
        record("frontend static assets", PASS, f"{len(refs)} references checked")


# ===========================================================================
# Check 9 — Docker is running
# ===========================================================================
def check_docker() -> None:
    rc, _, err = _run(["docker", "info"], timeout=10)
    if rc == 0:
        record("Docker daemon running", PASS)
    else:
        record(
            "Docker daemon running",
            WARN,
            "docker info failed — Docker is optional for non-containerised dev",
        )


# ===========================================================================
# Check 10 — Makefile does not contain bare `| tr ` invocations
# ===========================================================================
def check_makefile_no_tr() -> None:
    mf = PROJECT_ROOT / "Makefile"
    if not mf.exists():
        record("Makefile no bare `| tr`", SKIP, "Makefile not found")
        return

    content = mf.read_text(encoding="utf-8")
    # Look for `| tr ` that is NOT inside an ifeq($(OS),Windows_NT) block
    # Simple heuristic: count lines containing `| tr ` outside ifeq blocks
    offending = [
        ln.strip()
        for ln in content.splitlines()
        if "| tr " in ln and not ln.strip().startswith("#")
    ]
    if offending:
        record(
            "Makefile no bare `| tr`",
            FAIL,
            f"Found {len(offending)} line(s) — run: python scripts/fix_windows_compat.py",
        )
    else:
        record("Makefile no bare `| tr`", PASS)


# ===========================================================================
# Check 11 — Makefile does not contain bare `if [ -f` shell conditionals
# ===========================================================================
def check_makefile_no_bare_if_f() -> None:
    mf = PROJECT_ROOT / "Makefile"
    if not mf.exists():
        record("Makefile no bare `if [ -f`", SKIP, "Makefile not found")
        return

    content = mf.read_text(encoding="utf-8")
    offending = [
        ln.strip()
        for ln in content.splitlines()
        if re.search(r"@if \[ -f ", ln) and "ifeq" not in ln
    ]
    if offending:
        record(
            "Makefile no bare `if [ -f`",
            FAIL,
            f"Found {len(offending)} bare shell conditional(s) — run fix_windows_compat.py",
        )
    else:
        record("Makefile no bare `if [ -f`", PASS)


# ===========================================================================
# Check 12 — Port 8000 is free
# ===========================================================================
def check_port_free() -> None:
    if _tcp_reachable("127.0.0.1", 8000, timeout=1):
        record(
            "Port 8000 free",
            WARN,
            "Port 8000 is already in use — stop whatever is running there before make launch",
        )
    else:
        record("Port 8000 free", PASS)


# ===========================================================================
# Check 13 — scripts/validate_env.py exits 0
# ===========================================================================
def check_validate_env_script() -> None:
    script = PROJECT_ROOT / "scripts" / "validate_env.py"
    if not script.exists():
        record("scripts/validate_env.py", SKIP, "file not found")
        return

    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    rc, out, err = _run([python, str(script)], env=env, timeout=15)
    if rc == 0:
        record("scripts/validate_env.py exits 0", PASS)
    else:
        hint = (err or out).splitlines()[-1][:120] if (err or out) else "non-zero exit"
        record("scripts/validate_env.py exits 0", FAIL, hint)


# ===========================================================================
# Summary printer
# ===========================================================================
def print_summary() -> int:
    n_fail = sum(1 for _, s, _ in Results if s == FAIL)
    n_warn = sum(1 for _, s, _ in Results if s == WARN)
    n_pass = sum(1 for _, s, _ in Results if s == PASS)
    n_skip = sum(1 for _, s, _ in Results if s == SKIP)

    w = max(len(name) for name, _, _ in Results) + 2

    print()
    print("=" * 72)
    print("  LAUNCH READINESS REPORT")
    print("=" * 72)
    header = f"  {'Check':<{w}}  {'Status':<6}  Reason"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for name, status, reason in Results:
        sym = {"PASS": "PASS ", "FAIL": "FAIL ", "WARN": "WARN ", "SKIP": "SKIP "}[status]
        line = f"  {name:<{w}}  {sym}  {reason}"
        print(line)

    print("  " + "-" * (len(header) - 2))
    print(f"  {n_pass} passed  |  {n_fail} failed  |  {n_warn} warnings  |  {n_skip} skipped")
    print("=" * 72)

    if n_fail > 0:
        print(f"\n  [RESULT] NOT READY — {n_fail} check(s) must be fixed before launch.\n")
        return 1
    elif n_warn > 0:
        print(f"\n  [RESULT] READY WITH WARNINGS — {n_warn} item(s) to review.\n")
        return 0
    else:
        print("\n  [RESULT] LAUNCH READY — all checks passed.\n")
        return 0


# ===========================================================================
# Main
# ===========================================================================
def main() -> int:
    print()
    print("SwarmEnterprise v2 — Launch Readiness Checks")
    print(f"Platform: {platform.system()} {platform.release()} / Python {sys.version.split()[0]}")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    # Load .env early so all checks benefit
    _load_dotenv(PROJECT_ROOT / ".env")

    print("Running checks...")
    print()

    check_env_file()
    check_venv()
    check_requirements_installed()
    check_alembic_env_patched()
    check_alembic_migrate()
    check_models_importable()
    check_app_importable()
    check_frontend_assets()
    check_docker()
    check_makefile_no_tr()
    check_makefile_no_bare_if_f()
    check_port_free()
    check_validate_env_script()

    return print_summary()


if __name__ == "__main__":
    sys.exit(main())
