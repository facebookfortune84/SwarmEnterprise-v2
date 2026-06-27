#!/usr/bin/env bash
# restore_postgres.sh — SwarmOS PostgreSQL restore script
#
# Usage:  ./scripts/restore_postgres.sh <dump_file.sql.gz>
#
# Reads POSTGRES_USER, POSTGRES_DB from environment or .env.
# Drops and recreates the target database, then restores from the dump.
# Exit code 0 on success, 1 on failure or declined.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC2046
  export $(grep -v '^\s*#' "${ENV_FILE}" | grep -v '^\s*$' | xargs)
fi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONTAINER="${POSTGRES_CONTAINER:-swarmOS-postgres}"
POSTGRES_USER="${POSTGRES_USER:-swarm}"
POSTGRES_DB="${POSTGRES_DB:-swarm}"

# ---------------------------------------------------------------------------
# Argument check
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]] || [[ -z "${1}" ]]; then
  echo "Usage: $0 <dump_file.sql.gz>" >&2
  exit 1
fi

DUMP_FILE="$1"

if [[ ! -f "${DUMP_FILE}" ]]; then
  echo "ERROR: Dump file not found: ${DUMP_FILE}" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Container check
# ---------------------------------------------------------------------------
if ! docker inspect "${CONTAINER}" > /dev/null 2>&1; then
  echo "ERROR: Container '${CONTAINER}' is not running." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Warning + confirmation
# ---------------------------------------------------------------------------
echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│  ⚠  WARNING — DESTRUCTIVE OPERATION                            │"
echo "│                                                                 │"
echo "│  This will DROP and RECREATE the database '${POSTGRES_DB}'      │"
echo "│  in container '${CONTAINER}'.                                    │"
echo "│                                                                 │"
echo "│  ALL EXISTING DATA WILL BE PERMANENTLY LOST.                   │"
echo "│                                                                 │"
echo "│  Dump file : ${DUMP_FILE}                                       │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""
printf "Type YES to continue: "
read -r CONFIRM

if [[ "${CONFIRM}" != "YES" ]]; then
  echo "Restore cancelled."
  exit 1
fi

# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------
echo "[restore_postgres] Dropping existing database '${POSTGRES_DB}'..."
docker exec "${CONTAINER}" \
  psql -U "${POSTGRES_USER}" -d postgres \
  -c "DROP DATABASE IF EXISTS \"${POSTGRES_DB}\";" > /dev/null

echo "[restore_postgres] Creating fresh database '${POSTGRES_DB}'..."
docker exec "${CONTAINER}" \
  psql -U "${POSTGRES_USER}" -d postgres \
  -c "CREATE DATABASE \"${POSTGRES_DB}\";" > /dev/null

echo "[restore_postgres] Restoring from ${DUMP_FILE}..."
if gunzip -c "${DUMP_FILE}" | \
   docker exec -i "${CONTAINER}" \
     psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -q; then
  echo "[restore_postgres] Restore complete."
else
  echo "ERROR: Restore failed." >&2
  exit 1
fi

echo "[restore_postgres] Done."
exit 0
