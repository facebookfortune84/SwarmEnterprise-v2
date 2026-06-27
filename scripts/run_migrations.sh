#!/usr/bin/env bash
# run_migrations.sh — apply all pending Alembic migrations.
#
# Usage:
#   export DATABASE_URL="postgresql+psycopg2://user:pass@host/dbname"
#   bash scripts/run_migrations.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Guard: DATABASE_URL must be set
# ---------------------------------------------------------------------------
if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL environment variable is not set." >&2
  echo "       Export it before running this script, e.g.:" >&2
  echo "       export DATABASE_URL=\"postgresql+psycopg2://user:pass@host/dbname\"" >&2
  exit 1
fi

echo "Running Alembic migrations against: ${DATABASE_URL%%@*}@***"

# ---------------------------------------------------------------------------
# Run migrations
# ---------------------------------------------------------------------------
if alembic upgrade head; then
  echo "SUCCESS: all migrations applied."
else
  echo "FAILURE: migration run exited with error (see above)." >&2
  exit 1
fi
