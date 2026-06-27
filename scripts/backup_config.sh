#!/usr/bin/env bash
# backup_config.sh — SwarmOS configuration backup script
#
# Backs up:
#   .env
#   deploy/Caddyfile
#   deploy/Caddyfile.self-hosted  (if present)
#   alembic/versions/             (if present)
#   monitoring/*.yml
#
# Output: ./backups/config/YYYY-MM-DD_HH-MM/  →  compressed as .tar.gz
# Exit code 0 on success, 1 on failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Destination
# ---------------------------------------------------------------------------
TIMESTAMP="$(date -u '+%Y-%m-%d_%H-%M')"
BACKUP_DIR="${PROJECT_ROOT}/backups/config/${TIMESTAMP}"
ARCHIVE="${PROJECT_ROOT}/backups/config/${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

# ---------------------------------------------------------------------------
# Helper: copy a file preserving its relative path under BACKUP_DIR
# ---------------------------------------------------------------------------
backup_file() {
  local src="$1"
  local rel
  rel="$(realpath --relative-to="${PROJECT_ROOT}" "${src}")"
  local dest="${BACKUP_DIR}/${rel}"
  mkdir -p "$(dirname "${dest}")"
  cp -p "${src}" "${dest}"
  echo "  [ok] ${rel}"
}

# ---------------------------------------------------------------------------
# Helper: copy an entire directory preserving its relative path
# ---------------------------------------------------------------------------
backup_dir() {
  local src="$1"
  local rel
  rel="$(realpath --relative-to="${PROJECT_ROOT}" "${src}")"
  local dest="${BACKUP_DIR}/${rel}"
  mkdir -p "$(dirname "${dest}")"
  cp -rp "${src}" "${dest}"
  echo "  [ok] ${rel}/"
}

echo "[backup_config] Collecting files → ${BACKUP_DIR}"

# .env
[[ -f "${PROJECT_ROOT}/.env" ]]                              && backup_file "${PROJECT_ROOT}/.env"

# Caddyfile (required)
[[ -f "${PROJECT_ROOT}/deploy/Caddyfile" ]]                  && backup_file "${PROJECT_ROOT}/deploy/Caddyfile"

# Caddyfile.self-hosted (optional)
[[ -f "${PROJECT_ROOT}/deploy/Caddyfile.self-hosted" ]]      && backup_file "${PROJECT_ROOT}/deploy/Caddyfile.self-hosted"

# alembic/versions/ (optional)
[[ -d "${PROJECT_ROOT}/alembic/versions" ]]                  && backup_dir  "${PROJECT_ROOT}/alembic/versions"

# monitoring/*.yml
for yml_file in "${PROJECT_ROOT}"/monitoring/*.yml; do
  [[ -f "${yml_file}" ]] && backup_file "${yml_file}"
done

# ---------------------------------------------------------------------------
# Compress
# ---------------------------------------------------------------------------
echo "[backup_config] Compressing → ${ARCHIVE}"
tar -czf "${ARCHIVE}" -C "${PROJECT_ROOT}/backups/config" "${TIMESTAMP}"

# Remove the uncompressed staging directory
rm -rf "${BACKUP_DIR}"

echo "[backup_config] Archive: ${ARCHIVE} ($(du -sh "${ARCHIVE}" | cut -f1))"
echo "[backup_config] Done."
exit 0
