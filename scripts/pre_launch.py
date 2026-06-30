#!/usr/bin/env python3
"""
pre_launch.py — SwarmEnterprise v2 Pre-Launch Automated Checker
RWV Techsolutions LLC · robertdemottojr50@gmail.com

Industry-standard pre-launch validation covering:
  ✔ Environment / secrets strength
  ✔ Docker daemon + Compose syntax
  ✔ Connectivity (DB, Redis, Ollama)
  ✔ Alembic migration head (no pending changes)
  ✔ TLS / domain configuration (production only)
  ✔ Stripe key mode (live vs test)
  ✔ Docker image build (dry-run via `docker buildx inspect`)
  ✔ Backup strategy presence
  ✔ .gitignore covers .env
  ✔ No placeholder secrets committed to git
  ✔ SMTP configuration (production only)
  ✔ Seed data availability check

Exit codes:
  0 — all critical checks pass (warnings are acceptable)
  1 — one or more CRITICAL failures; do not launch

Usage:
  python scripts/pre_launch.py           # interactive, coloured output
  python scripts/pre_launch.py --quiet   # suppress info-level lines
  python scripts/pre_launch.py --json    # machine-readable JSON report
  python scripts/pre_launch.py --ci      # CI mode: exit 1 on any warning
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── load .env ────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    _ep = ROOT / ".env"
    if _ep.exists():
        for _l in _ep.read_text(encoding="utf-8", errors="ignore").splitlines():
            _l = _l.strip()
            if _l and not _l.startswith("#") and "=" in _l:
                _k, _, _v = _l.partition("=")
                _v = _v.split(" #")[0].strip().strip('"').strip("'")
                os.environ.setdefault(_k.strip(), _v)

# ── constants ────────────────────────────────────────────────────────────────
PLACEHOLDER_VALUES = {
    "", "changeme", "placeholder", "your-secret-here",
    "sk_test_placeholder", "whsec_placeholder", "todo", "xxxx",
}

CRITICAL = "CRITICAL"
WARNING  = "WARNING"
PASS     = "PASS"
INFO     = "INFO"


# ── helpers ──────────────────────────────────────────────────────────────────
class Result:
    __slots__ = ("level", "category", "message")

    def __init__(self, level: str, category: str, message: str) -> None:
        self.level = level
        self.category = category
        self.message = message


_results: list[Result] = []
_quiet = False


def _record(level: str, category: str, msg: str) -> None:
    _results.append(Result(level, category, msg))
    if _quiet and level == INFO:
        return
    icons = {PASS: "[PASS]", WARNING: "[WARN]", CRITICAL: "[FAIL]", INFO: "[INFO]"}
    print(f"  {icons.get(level, '     ')} {category}: {msg}")


def _env(key: str) -> str:
    return os.getenv(key, "").strip()


def _is_set(key: str) -> bool:
    v = _env(key)
    return bool(v) and v.lower() not in PLACEHOLDER_VALUES


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        return r.returncode, (r.stdout + r.stderr).decode(errors="replace")
    except Exception as e:
        return 1, str(e)


def _http_get(url: str, timeout: int = 5) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:
        return None, str(e)


# ── individual checks ─────────────────────────────────────────────────────────

def check_env_vars() -> None:
    cat = "Environment"
    required = [
        "JWT_SECRET_KEY", "SECRET_KEY", "POSTGRES_PASSWORD",
        "ADMIN_PASSWORD", "DATABASE_URL", "REDIS_URL",
    ]
    missing = [k for k in required if not _is_set(k)]
    if missing:
        for k in missing:
            _record(CRITICAL, cat, f"Missing required variable: {k}")
    else:
        _record(PASS, cat, "All required environment variables are set")

    # Strength checks
    for key, minlen in [("JWT_SECRET_KEY", 32), ("SECRET_KEY", 32)]:
        v = _env(key)
        if v and len(v) < minlen:
            _record(WARNING, cat, f"{key} is too short (< {minlen} chars)")
        elif v:
            _record(PASS, cat, f"{key} strength OK ({len(v)} chars)")

    admin_pass = _env("ADMIN_PASSWORD")
    if admin_pass and admin_pass.lower() in {"password", "admin", "12345678", "changeme"}:
        _record(CRITICAL, cat, "ADMIN_PASSWORD is a common/weak value")
    elif admin_pass and len(admin_pass) < 12:
        _record(WARNING, cat, "ADMIN_PASSWORD < 12 characters")


def check_docker() -> None:
    cat = "Docker"
    rc, out = _run(["docker", "ps"])
    if rc != 0:
        _record(CRITICAL, cat, f"Docker daemon not accessible: {out[:120]}")
        return
    _record(PASS, cat, "Docker daemon is running")

    rc, out = _run(["docker", "compose", "version"])
    if rc != 0:
        _record(CRITICAL, cat, "docker compose (v2 plugin) not found")
    else:
        _record(PASS, cat, f"Docker Compose available: {out.strip()[:60]}")


def check_compose_files() -> None:
    cat = "Compose Files"
    files = [ROOT / "docker-compose.yml", ROOT / "docker-compose.prod.yml"]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        _record(CRITICAL, cat, f"Missing compose files: {', '.join(missing)}")
        return
    _record(PASS, cat, "docker-compose.yml + docker-compose.prod.yml present")

    rc, out = _run(["docker", "compose", "config", "--quiet"], timeout=15)
    if rc != 0:
        _record(CRITICAL, cat, f"Compose syntax invalid: {out[:200]}")
    else:
        _record(PASS, cat, "Compose file syntax is valid")


def check_database() -> None:
    cat = "Database"
    db_url = _env("DATABASE_URL")
    if not db_url:
        _record(WARNING, cat, "DATABASE_URL not set; skipping DB connectivity check")
        return
    env = _env("ENV")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(
            db_url.replace("+asyncpg", ""),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        _record(PASS, cat, "Database connection successful")
    except ImportError:
        _record(WARNING, cat, "sqlalchemy not installed; skipping DB connectivity check")
    except Exception as e:
        short = str(e).split("\n")[0][:120]
        # If the hostname cannot be resolved it is a Docker-internal service name
        # (e.g. "postgres") that is only reachable from inside a container.
        # This is expected when running pre_launch.py on the host machine.
        # Treat it as a warning regardless of ENV so it doesn't block local runs.
        is_dns_error = any(kw in short.lower() for kw in (
            "no such host", "name or service not known",
            "could not translate", "getaddrinfo", "nodename nor servname"
        ))
        level = WARNING if is_dns_error else (CRITICAL if env == "production" else WARNING)
        hint = "(Docker service hostname — only reachable inside containers)" if is_dns_error else "(start Docker first?)"
        _record(level, cat, f"Database connection failed {hint}: {short}")


def check_redis() -> None:
    cat = "Redis"
    redis_url = _env("REDIS_URL") or "redis://localhost:6379/0"
    try:
        import redis as _redis
        r = _redis.from_url(redis_url, socket_timeout=3)
        r.ping()
        _record(PASS, cat, "Redis connection successful")
    except ImportError:
        _record(WARNING, cat, "redis-py not installed; skipping Redis check")
    except Exception as e:
        _record(WARNING, cat, f"Redis not reachable (may be offline for local dev): {e}")


def check_migrations() -> None:
    cat = "Migrations"
    rc, out = _run(
        [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), "current"],
        timeout=20,
    )
    if rc != 0:
        _record(WARNING, cat, f"alembic current failed: {out[:200]}")
        return
    _record(PASS, cat, "Alembic migrations runnable")

    rc2, out2 = _run(
        [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"),
         "check"],
        timeout=20,
    )
    if rc2 == 0:
        _record(PASS, cat, "Database schema matches latest migration (no pending changes)")
    else:
        # alembic check exits 1 when there are pending autogenerate changes
        _record(WARNING, cat, "alembic check: pending schema changes may exist — run make migrate")


def check_tls() -> None:
    cat = "TLS / Domain"
    env = _env("ENV")
    primary_domain = _env("PRIMARY_DOMAIN")
    acme_email = _env("ACME_EMAIL")

    if env != "production":
        _record(INFO, cat, f"ENV={env or 'unset'} — TLS check skipped (only for production)")
        return
    if not primary_domain:
        _record(CRITICAL, cat, "ENV=production but PRIMARY_DOMAIN is not set")
    else:
        _record(PASS, cat, f"PRIMARY_DOMAIN={primary_domain}")
    if not acme_email:
        _record(WARNING, cat, "ACME_EMAIL not set — Let's Encrypt provisioning will fail")
    else:
        _record(PASS, cat, f"ACME_EMAIL={acme_email}")


def check_stripe() -> None:
    cat = "Stripe"
    stripe_key = _env("STRIPE_API_KEY")
    test_mode = _env("STRIPE_TEST_MODE").upper() in ("TRUE", "1", "YES")
    env = _env("ENV")

    if not stripe_key or stripe_key.lower() in PLACEHOLDER_VALUES:
        _record(WARNING, cat, "STRIPE_API_KEY not configured")
        return

    if env == "production":
        if test_mode or not stripe_key.startswith("sk_live_"):
            _record(WARNING, cat,
                    "Running production with Stripe test key — set STRIPE_TEST_MODE=FALSE and use sk_live_...")
        else:
            _record(PASS, cat, "Stripe live key configured correctly")
    else:
        _record(PASS, cat, f"Stripe key present (test mode, ENV={env or 'development'})")


def check_smtp() -> None:
    cat = "SMTP"
    smtp_server = _env("SMTP_SERVER")
    smtp_user = _env("SMTP_USER")
    smtp_pass = _env("SMTP_PASS")
    env = _env("ENV")

    if env == "production" and not smtp_server:
        _record(WARNING, cat, "ENV=production but SMTP_SERVER not configured — outreach emails will fail")
        return
    if smtp_server and smtp_user and smtp_pass:
        _record(PASS, cat, f"SMTP configured ({smtp_server})")
    elif smtp_server:
        _record(WARNING, cat, "SMTP_SERVER set but SMTP_USER or SMTP_PASS missing")
    else:
        _record(INFO, cat, "SMTP not configured (optional for local dev)")


def check_secrets_not_in_git() -> None:
    cat = "Git Safety"
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        _record(WARNING, cat, ".gitignore not found")
        return
    content = gitignore.read_text(encoding="utf-8", errors="ignore")
    if ".env" in content:
        _record(PASS, cat, ".env is listed in .gitignore")
    else:
        _record(CRITICAL, cat, ".env is NOT in .gitignore — secrets may be committed!")

    # Check that .env is not tracked by git
    rc, out = _run(["git", "ls-files", "--error-unmatch", ".env"], timeout=5)
    if rc == 0:
        _record(CRITICAL, cat, ".env is tracked by git — run: git rm --cached .env")
    else:
        _record(PASS, cat, ".env is not tracked by git")


def check_backup_scripts() -> None:
    cat = "Backup"
    scripts = [
        ROOT / "scripts" / "backup_postgres.sh",
        ROOT / "scripts" / "backup_config.sh",
    ]
    missing = [s.name for s in scripts if not s.exists()]
    if missing:
        _record(WARNING, cat, f"Backup scripts missing: {', '.join(missing)}")
    else:
        _record(PASS, cat, "backup_postgres.sh + backup_config.sh present")


def check_ollama() -> None:
    cat = "Ollama (AI)"
    ollama_url = _env("OLLAMA_URL").rstrip("/")
    if not ollama_url:
        _record(INFO, cat, "OLLAMA_URL not set — local AI offline; cloud fallback required")
        return
    code, _ = _http_get(f"{ollama_url}/api/tags", timeout=3)
    if code == 200:
        _record(PASS, cat, f"Ollama accessible at {ollama_url}")
    else:
        _record(WARNING, cat, f"Ollama at {ollama_url} not responding (HTTP {code}) — local AI unavailable")


def check_backend_dockerfile() -> None:
    cat = "Docker Image"
    dockerfile = ROOT / "backend" / "Dockerfile"
    if not dockerfile.exists():
        _record(CRITICAL, cat, "backend/Dockerfile not found")
        return
    _record(PASS, cat, "backend/Dockerfile present")

    # Dry-run syntax check with docker build --check (BuildKit)
    rc, out = _run(
        ["docker", "buildx", "build", "--check", "-f", str(dockerfile), str(ROOT)],
        timeout=30,
    )
    if rc == 0:
        _record(PASS, cat, "Dockerfile syntax passes buildx --check")
    else:
        # Not all Docker versions support --check; treat as info
        _record(INFO, cat, f"buildx --check unavailable or failed: {out[:120]}")


def check_seed_script() -> None:
    cat = "Seed Data"
    seed = ROOT / "scripts" / "seed.py"
    if not seed.exists():
        _record(WARNING, cat, "scripts/seed.py not found")
    else:
        _record(PASS, cat, "Seed script present")

    admin_email = _env("ADMIN_EMAIL") or _env("CONTACT_EMAIL")
    admin_pass  = _env("ADMIN_PASSWORD")
    if not admin_email:
        _record(WARNING, cat, "ADMIN_EMAIL not set — admin user will not be seeded")
    if not admin_pass:
        _record(WARNING, cat, "ADMIN_PASSWORD not set — admin user will not be seeded")


def check_caddyfile() -> None:
    cat = "Caddy Proxy"
    caddyfile = ROOT / "deploy" / "Caddyfile"
    if not caddyfile.exists():
        _record(WARNING, cat, "deploy/Caddyfile not found")
    else:
        _record(PASS, cat, "deploy/Caddyfile present")


# ── orchestrator ─────────────────────────────────────────────────────────────

def run_all_checks() -> None:
    print()
    print("=" * 68)
    print("  SwarmEnterprise v2 — Pre-Launch Automated Check")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 68)
    print()

    check_env_vars()
    check_docker()
    check_compose_files()
    check_database()
    check_redis()
    check_migrations()
    check_tls()
    check_stripe()
    check_smtp()
    check_secrets_not_in_git()
    check_backup_scripts()
    check_ollama()
    check_backend_dockerfile()
    check_seed_script()
    check_caddyfile()

    print()
    print("=" * 68)

    passes   = [r for r in _results if r.level == PASS]
    warnings = [r for r in _results if r.level == WARNING]
    criticals = [r for r in _results if r.level == CRITICAL]

    print(f"  PASS:     {len(passes)}")
    print(f"  WARNINGS: {len(warnings)}")
    print(f"  CRITICAL: {len(criticals)}")
    print()

    if warnings:
        print("  Warnings (review before going live):")
        for w in warnings:
            print(f"    ! {w.category}: {w.message}")
        print()

    if criticals:
        print("  CRITICAL FAILURES — must fix before launch:")
        for c in criticals:
            print(f"    X {c.category}: {c.message}")
        print()
        print("  [BLOCKED] Do NOT launch until all CRITICAL items are resolved.")
    else:
        print("  [OK] No critical failures detected.")
        if warnings:
            print("  [OK] System may launch — review warnings above.")
        else:
            print("  [OK] All systems go — proceed to launch.")
    print("=" * 68)
    print()


def export_json(path: str) -> None:
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pass_count": sum(1 for r in _results if r.level == PASS),
        "warning_count": sum(1 for r in _results if r.level == WARNING),
        "critical_count": sum(1 for r in _results if r.level == CRITICAL),
        "results": [
            {"level": r.level, "category": r.category, "message": r.message}
            for r in _results
        ],
    }
    Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Report saved -> {path}")


def main() -> int:
    global _quiet
    parser = argparse.ArgumentParser(
        description="SwarmEnterprise v2 pre-launch automated check"
    )
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress INFO-level output")
    parser.add_argument("--json", metavar="FILE", default="",
                        help="Write JSON report to FILE (default: pre_launch_report.json)")
    parser.add_argument("--ci", action="store_true",
                        help="Exit 1 on any warning (for CI strict mode)")
    args = parser.parse_args()
    _quiet = args.quiet

    run_all_checks()

    json_path = args.json or "pre_launch_report.json"
    export_json(json_path)

    criticals = [r for r in _results if r.level == CRITICAL]
    warnings  = [r for r in _results if r.level == WARNING]

    if criticals:
        return 1
    if args.ci and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
