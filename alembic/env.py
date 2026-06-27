"""Alembic environment configuration for SwarmEnterprise v2.

Reads DATABASE_URL from os.environ and uses the SQLAlchemy metadata from
backend.db.models.Base so that autogenerate can reflect all 9 application
models (User, APIKey, CompanyTenant, Deployment, Ticket, Project, Lead,
UsageEvent, ProcessedEvent).
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Inject DATABASE_URL from the environment, overriding the placeholder in
# alembic.ini so no credentials are ever stored in config files.
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Export it before running Alembic commands."
    )
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — import Base from the canonical models module so that
# autogenerate compares the live DB schema against all declared models.
# ---------------------------------------------------------------------------
from backend.db.models import Base  # noqa: E402  (import after env setup)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode
# Emits SQL to stdout without connecting to the database.
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
# Online migration mode
# Connects to the database and applies migrations transactionally.
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
# Entry point — Alembic selects the correct mode automatically.
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
