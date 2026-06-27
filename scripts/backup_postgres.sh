#!/usr/bin/env bash
# backup_postgres.sh — SwarmOS PostgreSQL backup script
#
# Uses docker exec to run pg_dump on the postgres container.
# Saves dump to ./backups/postgres/YYYY-MM-DD_HH-MM.sql.gz
# Deletes dumps older than 30 days.
#
# Requires: POSTGRES_USER, POSTGRES_DB (reads from .env if present)
# Exit code 0 on success, 1 on failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Load .env if present (values are NOT exported so they don't bleed into the
# surrounding shell; only this script's sub-processes inherit them via env).
# ---------------------------------------------------------------------------
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^\s*#' "${ENV_FILE}" | grep -v '^\s*$' | xargs)
fi

# ---------------------------------------------------------------------------
# Configuration (override via env or .env)
# ---------------------------------------------------------------------------
CONTAINER="${POSTGRES_CONTAINER:-swarmOS-postgres}"
POSTGRES_USER="${POSTGRES_USER:-swarm}"
POSTGRES_DB="${POSTGRES_DB:-swarm}"
BACKUP_ROOT="${PROJECT_ROOT}/backups/postgres"
RETENTION_DAYS=30

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
if [[ -z "${POSTGRES_USER}" ]] || [[ -z "${POSTGRES_DB}" ]]; then
  echo "ERROR: POSTGRES_USER and POSTGRES_DB must be set." >&2
  exit 1
fi

if ! docker inspect "${CONTAINER}" > /dev/null 2>&1; then
  echo "ERROR: Container '${CONTAINER}' is not running." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Prepare destination
# ---------------------------------------------------------------------------
TIMESTAMP="$(date -u '+%Y-%m-%d_%H-%M')"
DUMP_FILE="${BACKUP_ROOT}/${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_ROOT}"

# ---------------------------------------------------------------------------
# Dump
# ---------------------------------------------------------------------------
echo "[backup_postgres] Starting pg_dump for db='${POSTGRES_DB}' user='${POSTGRES_USER}' → ${DUMP_FILE}"

if docker exec "${CONTAINER}" \
     pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "${DUMP_FILE}"; then
  echo "[backup_postgres] Dump complete: ${DUMP_FILE} ($(du -sh "${DUMP_FILE}" | cut -f1))"
else
  echo "ERROR: pg_dump failed." >&2
  rm -f "${DUMP_FILE}"
  exit 1
fi

# ---------------------------------------------------------------------------
# Verify the file is non-empty
# ---------------------------------------------------------------------------
if [[ ! -s "${DUMP_FILE}" ]]; then
  echo "ERROR: Dump file is empty — aborting." >&2
  rm -f "${DUMP_FILE}"
  exit 1
fi

# ---------------------------------------------------------------------------
# Prune old backups
# ---------------------------------------------------------------------------
echo "[backup_postgres] Pruning dumps older than ${RETENTION_DAYS} days..."
find "${BACKUP_ROOT}" -maxdepth 1 -name '*.sql.gz' \
  -mtime "+${RETENTION_DAYS}" -print -delete

echo "[backup_postgres] Done."
exit 0
