#!/usr/bin/env python3
"""
seed.py — SwarmEnterprise v2 database seed script
RWV Techsolutions LLC · robertdemottojr50@gmail.com

Creates initial required data:
  - Admin user        (ADMIN_EMAIL / ADMIN_PASSWORD env vars)
  - Default roles     (admin, operator, viewer)
  - Ticket categories (bug, feature, task, question)
  - Usage event types
  - Default system configuration entries

Idempotent: safe to run multiple times. Nothing is duplicated.

Usage
-----
  python scripts/seed.py              # seed (skip if already done)
  python scripts/seed.py --check      # exit 0 already seeded, exit 1 if not
  python scripts/seed.py --force      # reseed even if already seeded
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: make sure project root is on sys.path and .env is loaded
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=False)
except ImportError:
    # Minimal .env parser if python-dotenv is not installed
    _env_file = _ROOT / ".env"
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _v = _v.split(" #")[0].strip().strip('"').strip("'")
            os.environ.setdefault(_k.strip(), _v)


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        # SQLAlchemy 2 needs 'postgresql://' not 'postgresql+asyncpg://' for sync
        url = url.replace("postgresql+asyncpg://", "postgresql://").replace(
            "postgres+asyncpg://", "postgresql://"
        )
        return url
    # Build from parts
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "swarm")
    user = os.getenv("POSTGRES_USER", "swarm")
    pw = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


def _connect():
    """Return a psycopg2 connection (or raise with a friendly message)."""
    try:
        import psycopg2  # type: ignore
    except ImportError:
        print(
            "[ERROR] psycopg2 is not installed. Run: pip install psycopg2-binary", file=sys.stderr
        )
        sys.exit(2)

    url = _get_database_url()
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = False
        return conn
    except Exception as exc:
        print(f"[ERROR] Cannot connect to database: {exc}", file=sys.stderr)
        print(f"        DATABASE_URL used: {url[:60]}…", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Password hashing (bcrypt preferred, PBKDF2-SHA256 fallback)
# ---------------------------------------------------------------------------
def _hash_password(plain: str) -> str:
    try:
        import bcrypt  # type: ignore

        hashed: bytes = bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12))
        return hashed.decode()
    except ImportError:
        pass
    # PBKDF2-SHA256 fallback (stdlib)
    import base64

    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, 260_000)
    encoded_salt = base64.b64encode(salt).decode()
    encoded_dk = base64.b64encode(dk).decode()
    return f"pbkdf2:sha256:260000${encoded_salt}${encoded_dk}"


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------
_NOW = datetime.now(timezone.utc)


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s LIMIT 1;",
        (table,),
    )
    return cur.fetchone() is not None


def _ensure_seed_table(cur) -> None:
    """Create a tiny sentinel table so --check works without relying on app tables."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS _seed_meta (
            key   TEXT PRIMARY KEY,
            value TEXT,
            seeded_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )


def _is_seeded(cur) -> bool:
    _ensure_seed_table(cur)
    cur.execute("SELECT value FROM _seed_meta WHERE key = 'seeded';")
    row = cur.fetchone()
    return row is not None and row[0] == "true"


def _mark_seeded(cur) -> None:
    cur.execute(
        """
        INSERT INTO _seed_meta (key, value, seeded_at)
        VALUES ('seeded', 'true', NOW())
        ON CONFLICT (key) DO UPDATE SET value = 'true', seeded_at = NOW();
        """
    )


# ---------------------------------------------------------------------------
# Individual seed functions  (each is idempotent via ON CONFLICT DO NOTHING)
# ---------------------------------------------------------------------------


def seed_roles(cur) -> None:
    if not _table_exists(cur, "roles"):
        print("  [SKIP] 'roles' table not found — skipping role seed.")
        return
    roles = [
        ("admin", "Full system administrator access"),
        ("operator", "Can manage agents, jobs, and tenants"),
        ("viewer", "Read-only access"),
    ]
    for name, description in roles:
        cur.execute(
            """
            INSERT INTO roles (name, description, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING;
            """,
            (name, description, _NOW),
        )
    print(f"  [OK]   Roles: {[r[0] for r in roles]}")


def seed_admin_user(cur) -> None:
    if not _table_exists(cur, "users"):
        print("  [SKIP] 'users' table not found — skipping admin user seed.")
        return

    email = os.getenv("ADMIN_EMAIL", "admin@swarmenterprise.local")
    password = os.getenv("ADMIN_PASSWORD", "ChangeMe!SwarmAdmin2024")
    pw_hash = _hash_password(password)

    cur.execute(
        """
        INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser, created_at)
        VALUES (%s, %s, %s, TRUE, TRUE, %s)
        ON CONFLICT (email) DO NOTHING;
        """,
        (email, pw_hash, "System Administrator", _NOW),
    )

    # Assign admin role if junction table exists
    if _table_exists(cur, "user_roles"):
        cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1;", (email,))
        user_row = cur.fetchone()
        cur.execute("SELECT id FROM roles WHERE name = 'admin' LIMIT 1;")
        role_row = cur.fetchone()
        if user_row and role_row:
            cur.execute(
                """
                INSERT INTO user_roles (user_id, role_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (user_row[0], role_row[0]),
            )

    print(f"  [OK]   Admin user: {email}")
    if password == "ChangeMe!SwarmAdmin2024":
        print(
            "  [WARN] Using default ADMIN_PASSWORD — set ADMIN_PASSWORD in .env before going to production!"
        )


def seed_ticket_categories(cur) -> None:
    if not _table_exists(cur, "ticket_categories"):
        print("  [SKIP] 'ticket_categories' table not found — skipping.")
        return
    categories = [
        ("bug", "Software defect or unexpected behaviour"),
        ("feature", "New feature request or enhancement"),
        ("task", "General work item or chore"),
        ("question", "Question or clarification needed"),
    ]
    for name, description in categories:
        cur.execute(
            """
            INSERT INTO ticket_categories (name, description, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING;
            """,
            (name, description, _NOW),
        )
    print(f"  [OK]   Ticket categories: {[c[0] for c in categories]}")


def seed_usage_event_types(cur) -> None:
    if not _table_exists(cur, "usage_event_types"):
        print("  [SKIP] 'usage_event_types' table not found — skipping.")
        return
    event_types = [
        ("api_call", "REST API request"),
        ("agent_run", "AI agent task execution"),
        ("token_consumed", "LLM token consumed"),
        ("file_generated", "Output file created by factory engine"),
        ("email_sent", "Outbound email dispatched"),
        ("payment_received", "Stripe payment confirmed"),
    ]
    for name, description in event_types:
        cur.execute(
            """
            INSERT INTO usage_event_types (name, description, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING;
            """,
            (name, description, _NOW),
        )
    print(f"  [OK]   Usage event types: {[e[0] for e in event_types]}")


def seed_system_config(cur) -> None:
    if not _table_exists(cur, "system_config"):
        print("  [SKIP] 'system_config' table not found — skipping.")
        return
    config_entries = [
        ("company_name", "RWV Techsolutions LLC", "Legal company name"),
        ("product_name", "SwarmEnterprise v2", "Product display name"),
        ("contact_email", "robertdemottojr50@gmail.com", "Primary contact email"),
        ("onboarding_done", "false", "Set to true after first-run wizard"),
        ("version", "2.0.0", "Application version"),
    ]
    for key, value, description in config_entries:
        cur.execute(
            """
            INSERT INTO system_config (key, value, description, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (key) DO NOTHING;
            """,
            (key, value, description, _NOW),
        )
    print(f"  [OK]   System config: {[c[0] for c in config_entries]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_seed(force: bool = False) -> int:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            _ensure_seed_table(cur)

            if not force and _is_seeded(cur):
                print("[INFO] Database already seeded. Use --force to reseed.")
                return 0

            print("Seeding SwarmEnterprise v2 initial data …")
            print(f"  Target: {_get_database_url()[:60]}…")
            print()

            seed_roles(cur)
            seed_admin_user(cur)
            seed_ticket_categories(cur)
            seed_usage_event_types(cur)
            seed_system_config(cur)

            _mark_seeded(cur)
            conn.commit()

        print()
        print("[OK]  Seed complete.")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


def run_check() -> int:
    """Exit 0 if already seeded, 1 if not."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            _ensure_seed_table(cur)
            conn.commit()
            if _is_seeded(cur):
                return 0
            return 1
    except Exception:
        return 1
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SwarmEnterprise v2 database seed script — RWV Techsolutions LLC",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 if already seeded, 1 if not. Does not write any data.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reseed even if the database is already marked as seeded.",
    )
    args = parser.parse_args(argv)

    if args.check:
        return run_check()
    return run_seed(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
