"""Alembic environment configuration for SwarmEnterprise v2.

URL resolution priority (mirrors backend/db/session.py):
  1. SWARM_DB_URL  — explicit override for Alembic / local dev
  2. DATABASE_URL  — application env var (may use async driver; rewritten to sync)
  3. Local SQLite  — pg_data/swarm_enterprise.db relative to project root

All variables are loaded from .env automatically before any os.environ access,
so `alembic upgrade head` works without manually exporting variables.  An
already-exported value in the shell always takes precedence over .env (override=False).

Async-driver rewriting:
  sqlite+aiosqlite → sqlite
  postgresql+asyncpg / +aiopg → postgresql
  mysql+aiomysql → mysql

SQLite path fixup:
  If the SQLite path starts with /app/ (a Docker-only path) and that directory
  does not exist on the local filesystem, the DB file is rewritten to a local
  path at <project-root>/pg_data/swarm_enterprise.db so Alembic can run locally.
"""

import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Load .env from project root (two levels up from this file in alembic/).
# override=False → shell-exported values always win.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(_PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on the process environment

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config


# ---------------------------------------------------------------------------
# Determine a synchronous, locally-reachable database URL.
# ---------------------------------------------------------------------------
def _resolve_db_url() -> str:
    """Return a synchronous SQLAlchemy URL suitable for Alembic."""
    # Priority 1: explicit Alembic / local-dev override
    url = os.environ.get("SWARM_DB_URL", "").strip()

    # Priority 2: application DATABASE_URL
    if not url:
        url = os.environ.get("DATABASE_URL", "").strip()

    # Priority 3: local SQLite fallback (mirrors backend/db/session.py)
    if not url:
        db_dir = Path(os.environ.get("SWARM_PG_DIR", str(_PROJECT_ROOT / "pg_data")))
        db_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(db_dir / 'swarm_enterprise.db').as_posix()}"

    # Rewrite async drivers → synchronous equivalents
    _ASYNC_MAP = {
        "sqlite+aiosqlite://": "sqlite://",
        "postgresql+asyncpg://": "postgresql://",
        "postgresql+aiopg://": "postgresql://",
        "mysql+aiomysql://": "mysql://",
    }
    for async_prefix, sync_prefix in _ASYNC_MAP.items():
        if url.startswith(async_prefix):
            url = sync_prefix + url[len(async_prefix) :]
            break

    # SQLite path fixup: /app/... is a Docker-only path.
    # If that directory doesn't exist locally, redirect to a local file.
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        # Relative sqlite URL — fine as-is
        pass
    elif url.startswith("sqlite:////"):
        # Absolute path (4 slashes on Unix, 3+drive on Windows)
        raw_path = url[len("sqlite:///") :]  # e.g. /app/swarm.db  or  C:/...
        if not Path(raw_path).parent.exists():
            db_dir = _PROJECT_ROOT / "pg_data"
            db_dir.mkdir(parents=True, exist_ok=True)
            local_path = db_dir / "swarm_enterprise.db"
            url = f"sqlite:///{local_path.as_posix()}"

    return url


_db_url = _resolve_db_url()
config.set_main_option("sqlalchemy.url", _db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — import Base so autogenerate reflects all declared models.
# ---------------------------------------------------------------------------
from backend.db.models import Base  # noqa: E402  (import after env setup)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode — emits SQL to stdout without connecting.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode — connects and applies migrations transactionally.
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
