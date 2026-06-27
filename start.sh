#!/usr/bin/env bash
# start.sh — SwarmEnterprise v2 launch script
# RWV Techsolutions LLC · robertdemottojr50@gmail.com
set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
  BOLD='\033[1m'; RESET='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BOLD=''; RESET=''
fi

info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()   { error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Step 1 — Load .env then validate required environment variables
# ---------------------------------------------------------------------------
info "Loading environment …"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ -f "${REPO_ROOT}/.env" ]; then
  # Export every non-comment, non-blank line
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
  info "Loaded ${REPO_ROOT}/.env"
else
  warn ".env not found — relying on process environment"
fi

# Required vars: either DATABASE_URL or the individual POSTGRES_* set
_missing=()

# DATABASE_URL or POSTGRES_* group
if [ -z "${DATABASE_URL:-}" ]; then
  for v in POSTGRES_HOST POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
    [ -z "${!v:-}" ] && _missing+=("$v")
  done
fi

for v in JWT_SECRET_KEY SECRET_KEY; do
  [ -z "${!v:-}" ] && _missing+=("$v")
done

if [ ${#_missing[@]} -gt 0 ]; then
  error "The following required environment variables are not set:"
  for v in "${_missing[@]}"; do
    echo "    $v"
  done
  echo ""
  echo "  Copy .env.example → .env and fill in the missing values:"
  echo "    cp .env.example .env"
  echo "    python scripts/generate_secrets.py  # to generate JWT_SECRET_KEY / SECRET_KEY"
  exit 1
fi

# Optional vars — apply defaults
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
PORT="${PORT:-${BACKEND_PORT:-8000}}"
DEPLOY_PROFILE="${DEPLOY_PROFILE:-local}"

info "Environment validated."

# ---------------------------------------------------------------------------
# Step 2 — Check binary dependencies
# ---------------------------------------------------------------------------
info "Checking dependencies …"

_check_dep() {
  local cmd="$1"; local install_hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    die "'${cmd}' not found. ${install_hint}"
  fi
}

_check_dep docker    "Install Docker Desktop from https://docs.docker.com/get-docker/"
_check_dep python3   "Install Python 3.11+ from https://www.python.org/downloads/"

# Accept both 'docker-compose' (v1) and 'docker compose' (v2 plugin)
if command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  DC="docker compose"
else
  die "'docker compose' not found. Install Docker Desktop (includes Compose plugin): https://docs.docker.com/compose/install/"
fi

info "Dependencies OK  (compose: ${DC})"

# ---------------------------------------------------------------------------
# Step 3 — Verify Docker daemon is running
# ---------------------------------------------------------------------------
info "Checking Docker daemon …"
if ! docker info >/dev/null 2>&1; then
  die "Docker daemon is not running. Start Docker Desktop (or: sudo systemctl start docker) and retry."
fi
info "Docker daemon is running."

# ---------------------------------------------------------------------------
# Step 4 — Run database migrations
# ---------------------------------------------------------------------------
info "Running database migrations (alembic upgrade head) …"
if ! (cd "${REPO_ROOT}" && python3 -m alembic upgrade head); then
  die "Database migration failed. Check your DATABASE_URL / POSTGRES_* settings and ensure the DB is reachable."
fi
info "Migrations complete."

# ---------------------------------------------------------------------------
# Step 5 — Seed initial data if needed
# ---------------------------------------------------------------------------
info "Checking seed state …"
SEED_SCRIPT="${REPO_ROOT}/scripts/seed.py"
if [ -f "${SEED_SCRIPT}" ]; then
  if ! python3 "${SEED_SCRIPT}" --check 2>/dev/null; then
    info "Seeding initial data …"
    if ! python3 "${SEED_SCRIPT}"; then
      warn "Seed script failed — continuing startup (non-fatal)."
    else
      info "Seed complete."
    fi
  else
    info "Database already seeded — skipping."
  fi
else
  warn "scripts/seed.py not found — skipping seed step."
fi

# ---------------------------------------------------------------------------
# Step 6 — Start services via docker compose
# ---------------------------------------------------------------------------
info "Starting services (profile: ${DEPLOY_PROFILE}) …"

COMPOSE_FILES="-f ${REPO_ROOT}/docker-compose.yml"

case "${DEPLOY_PROFILE}" in
  production*)
    if [ -f "${REPO_ROOT}/docker-compose.prod.yml" ]; then
      COMPOSE_FILES="${COMPOSE_FILES} -f ${REPO_ROOT}/docker-compose.prod.yml"
    fi
    PROFILES="--profile proxy --profile postgres --profile workers"
    ;;
  staging)
    PROFILES="--profile postgres --profile workers"
    ;;
  *)
    # local / local-laptop-ollama
    PROFILES=""
    if [ -f "${REPO_ROOT}/docker-compose.local-laptop-ollama.yml" ]; then
      COMPOSE_FILES="${COMPOSE_FILES} -f ${REPO_ROOT}/docker-compose.local-laptop-ollama.yml"
    fi
    ;;
esac

# shellcheck disable=SC2086
${DC} ${COMPOSE_FILES} ${PROFILES} up -d --build
info "Docker services started."

# ---------------------------------------------------------------------------
# Step 7 — Wait for /health to pass (60 s timeout)
# ---------------------------------------------------------------------------
HEALTH_URL="http://localhost:${PORT}/health"
TIMEOUT=60
INTERVAL=3
ELAPSED=0

info "Waiting for health check at ${HEALTH_URL} …"
until curl -sf "${HEALTH_URL}" >/dev/null 2>&1; do
  if [ "${ELAPSED}" -ge "${TIMEOUT}" ]; then
    die "Health check timed out after ${TIMEOUT}s. Check logs: ${DC} logs backend"
  fi
  sleep "${INTERVAL}"
  ELAPSED=$((ELAPSED + INTERVAL))
done
info "Health check passed (${ELAPSED}s)."

# ---------------------------------------------------------------------------
# Step 8 — Print summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  SwarmEnterprise v2 — RUNNING${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${BOLD}API${RESET}      http://localhost:${PORT}"
echo -e "  ${BOLD}Docs${RESET}     http://localhost:${PORT}/docs"
echo -e "  ${BOLD}Health${RESET}   http://localhost:${PORT}/health"
echo -e "  ${BOLD}Metrics${RESET}  http://localhost:${PORT}/metrics"
echo -e "  ${BOLD}Profile${RESET}  ${DEPLOY_PROFILE}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Logs:    ${DC} logs -f backend"
echo "  Stop:    ./stop.sh  or  make stop"
echo ""
