#!/usr/bin/env bash
# docker-entrypoint.sh — SwarmEnterprise v2
# Runs pre-start checks and then hands off to the CMD.
set -euo pipefail

echo "[entrypoint] SwarmEnterprise v2 starting …"

# 1. Wait for PostgreSQL if DATABASE_URL is set to postgres
if [[ "${DATABASE_URL:-}" == postgres* ]] || [[ "${DATABASE_URL:-}" == postgresql* ]]; then
    echo "[entrypoint] Waiting for PostgreSQL …"
    for i in $(seq 1 30); do
        python -c "
import os, sys
try:
    import psycopg2
    psycopg2.connect(os.environ['DATABASE_URL'].replace('+asyncpg','').replace('postgresql+psycopg2','postgresql'))
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" && break || true
        echo "  Attempt ${i}/30 — waiting 2s …"
        sleep 2
    done
    echo "[entrypoint] PostgreSQL is ready."
fi

# 2. Wait for Redis if REDIS_URL is set
if [[ -n "${REDIS_URL:-}" ]]; then
    echo "[entrypoint] Checking Redis …"
    python -c "
import os, sys, time
try:
    import redis
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
    r.ping()
    print('[entrypoint] Redis is ready.')
except Exception as e:
    print(f'[entrypoint] Redis not reachable: {e}', file=sys.stderr)
    # Non-fatal: continue startup; Redis may become available later
" || true
fi

# 3. Run Alembic migrations (idempotent — safe to run on every start)
if [[ "${RUN_MIGRATIONS:-true}" == "true" ]]; then
    echo "[entrypoint] Running database migrations …"
    alembic upgrade head && echo "[entrypoint] Migrations complete." || {
        echo "[entrypoint] Migration failed — aborting." >&2
        exit 1
    }
fi

echo "[entrypoint] Handing off to: $*"
exec "$@"
