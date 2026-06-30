#!/usr/bin/env bash
# =============================================================================
# start.sh — SwarmEnterprise v2 Unified Launch Script
# RWV Techsolutions LLC · robertdemottojr50@gmail.com
#
# Usage:
#   ./start.sh                        # auto-detect DEPLOY_PROFILE from .env
#   DEPLOY_PROFILE=production ./start.sh
#   DEPLOY_PROFILE=staging    ./start.sh
#   ./start.sh --skip-migrations      # skip alembic (fast restart)
#   ./start.sh --skip-smoke           # skip smoke tests after start
#   ./start.sh --verify-live          # run verify_live.py after all services up
#
# Exit codes:
#   0 — services running and healthy
#   1 — fatal error (environment, migrations, Docker)
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
  BOLD='\033[1m'; CYAN='\033[0;36m'; RESET='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; BOLD=''; CYAN=''; RESET=''
fi

step()  { echo -e "\n${CYAN}${BOLD}▶ $*${RESET}"; }
info()  { echo -e "  ${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "  ${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "  ${RED}[ERROR]${RESET} $*" >&2; }
die()   { error "$*"; exit 1; }
ok()    { echo -e "  ${GREEN}[OK]${RESET}    $*"; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
SKIP_MIGRATIONS=false
SKIP_SMOKE=false
VERIFY_LIVE=false

for arg in "$@"; do
  case "$arg" in
    --skip-migrations) SKIP_MIGRATIONS=true ;;
    --skip-smoke)      SKIP_SMOKE=true ;;
    --verify-live)     VERIFY_LIVE=true ;;
    --help|-h)
      echo "Usage: $0 [--skip-migrations] [--skip-smoke] [--verify-live]"
      exit 0
      ;;
    *) warn "Unknown argument: $arg (ignored)" ;;
  esac
done

# ---------------------------------------------------------------------------
# Track start time for summary
# ---------------------------------------------------------------------------
START_TS=$(date +%s)

# ---------------------------------------------------------------------------
# Step 0 — Banner
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${CYAN}  SwarmEnterprise v2 — Unified Launch Sequence${RESET}"
echo -e "${BOLD}${CYAN}  $(date -u '+%Y-%m-%d %H:%M UTC')${RESET}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ---------------------------------------------------------------------------
# Step 1 — Load and validate environment
# ---------------------------------------------------------------------------
step "Step 1 / 8 — Environment"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

if [ -f "${REPO_ROOT}/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
  ok "Loaded ${REPO_ROOT}/.env"
else
  warn ".env not found — relying on process environment"
  warn "Run: cp .env.example .env  and  python scripts/generate_secrets.py"
fi

# Required vars check
_missing=()
if [ -z "${DATABASE_URL:-}" ]; then
  for v in POSTGRES_HOST POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD; do
    [ -z "${!v:-}" ] && _missing+=("$v")
  done
fi
for v in JWT_SECRET_KEY SECRET_KEY; do
  [ -z "${!v:-}" ] && _missing+=("$v")
done

if [ ${#_missing[@]} -gt 0 ]; then
  error "Required environment variables missing:"
  for v in "${_missing[@]}"; do
    echo "      $v"
  done
  echo ""
  echo "    Fix: cp .env.example .env && python scripts/generate_secrets.py"
  exit 1
fi

# Apply defaults
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
PORT="${PORT:-${BACKEND_PORT:-8000}}"
DEPLOY_PROFILE="${DEPLOY_PROFILE:-local}"

ok "Environment validated (DEPLOY_PROFILE=${DEPLOY_PROFILE})"

# ---------------------------------------------------------------------------
# Step 2 — Dependency checks
# ---------------------------------------------------------------------------
step "Step 2 / 8 — Dependencies"

_check_dep() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "'$1' not found. $2"
  fi
  ok "$1 ✓"
}

_check_dep docker  "Install Docker Desktop: https://docs.docker.com/get-docker/"
_check_dep python3 "Install Python 3.11+:   https://www.python.org/downloads/"

# Docker Compose (v2 plugin preferred, v1 standalone accepted)
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
  ok "docker compose (v2) ✓"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
  warn "Using legacy docker-compose v1 — consider upgrading to Docker Desktop with Compose v2 plugin"
else
  die "'docker compose' not found. Install Docker Desktop: https://docs.docker.com/compose/install/"
fi

# ---------------------------------------------------------------------------
# Step 3 — Docker daemon check
# ---------------------------------------------------------------------------
step "Step 3 / 8 — Docker Daemon"
if ! docker info >/dev/null 2>&1; then
  die "Docker daemon not running. Start Docker Desktop (or: sudo systemctl start docker) and retry."
fi
ok "Docker daemon is running"

# ---------------------------------------------------------------------------
# Step 4 — Pre-launch validation (fast)
# ---------------------------------------------------------------------------
step "Step 4 / 8 — Pre-Launch Checks"
if command -v python3 >/dev/null 2>&1 && [ -f "${REPO_ROOT}/scripts/pre_launch.py" ]; then
  python3 "${REPO_ROOT}/scripts/pre_launch.py" --quiet || {
    warn "Pre-launch check reported issues — see pre_launch_report.json"
    warn "Continuing startup; fix critical items before production traffic."
  }
else
  warn "scripts/pre_launch.py not found — skipping automated pre-launch check"
fi

# ---------------------------------------------------------------------------
# Step 5 — Create required directories
# ---------------------------------------------------------------------------
step "Step 5 / 8 — Directories & Storage"
mkdir -p "${REPO_ROOT}/pg_data"        \
         "${REPO_ROOT}/output/storage" \
         "${REPO_ROOT}/output/src"     \
         "${REPO_ROOT}/logs"           \
         "${REPO_ROOT}/backups/config" \
         "${REPO_ROOT}/backups/postgres"
ok "Required directories ready"

# ---------------------------------------------------------------------------
# Step 6 — Start Docker infrastructure
# ---------------------------------------------------------------------------
step "Step 6 / 8 — Docker Infrastructure"

COMPOSE_FILES="-f ${REPO_ROOT}/docker-compose.yml"
PROFILES=""

case "${DEPLOY_PROFILE}" in
  production*)
    if [ -f "${REPO_ROOT}/docker-compose.prod.yml" ]; then
      COMPOSE_FILES="${COMPOSE_FILES} -f ${REPO_ROOT}/docker-compose.prod.yml"
    fi
    PROFILES="--profile proxy --profile postgres --profile workers"
    info "Production profile: proxy + postgres + workers"
    ;;
  staging)
    if [ -f "${REPO_ROOT}/docker-compose.prod.yml" ]; then
      COMPOSE_FILES="${COMPOSE_FILES} -f ${REPO_ROOT}/docker-compose.prod.yml"
    fi
    PROFILES="--profile postgres --profile workers"
    info "Staging profile: postgres + workers"
    ;;
  *)
    # local / local-laptop-ollama
    if [ -f "${REPO_ROOT}/docker-compose.local-laptop-ollama.yml" ]; then
      COMPOSE_FILES="${COMPOSE_FILES} -f ${REPO_ROOT}/docker-compose.local-laptop-ollama.yml"
    fi
    info "Local profile: base services only"
    ;;
esac

# Pull latest images first (non-fatal if no network)
info "Pulling latest images…"
# shellcheck disable=SC2086
${DC} ${COMPOSE_FILES} ${PROFILES} pull --quiet 2>/dev/null || warn "Image pull skipped (offline?)"

# Build local images (backend)
info "Building local images…"
# shellcheck disable=SC2086
${DC} ${COMPOSE_FILES} build --quiet

# Start the stack
info "Starting services (detached)…"
# shellcheck disable=SC2086
${DC} ${COMPOSE_FILES} ${PROFILES} up -d --remove-orphans

ok "Docker services started"

# ---------------------------------------------------------------------------
# Step 7 — Database migrations + seed
# ---------------------------------------------------------------------------
step "Step 7 / 8 — Database Migrations & Seed"

if [ "${SKIP_MIGRATIONS}" = "true" ]; then
  warn "Skipping migrations (--skip-migrations)"
else
  MIGRATION_TIMEOUT=120
  info "Running alembic upgrade head (timeout: ${MIGRATION_TIMEOUT}s)…"
  if ! timeout "${MIGRATION_TIMEOUT}" python3 -m alembic upgrade head 2>&1; then
    error "Database migration failed."
    error "Troubleshoot: ${DC} logs postgres  →  check DATABASE_URL in .env"
    # Give containers time to output logs before dying
    sleep 3
    die "Migration failure — aborting launch."
  fi
  ok "Migrations complete"

  # Seed initial data (idempotent)
  SEED_SCRIPT="${REPO_ROOT}/scripts/seed.py"
  if [ -f "${SEED_SCRIPT}" ]; then
    if ! python3 "${SEED_SCRIPT}" --check 2>/dev/null; then
      info "Seeding initial data…"
      python3 "${SEED_SCRIPT}" && ok "Seed complete" || warn "Seed failed (non-fatal — continuing)"
    else
      info "Database already seeded — skipping seed"
    fi
  else
    warn "scripts/seed.py not found — skipping seed"
  fi
fi

# ---------------------------------------------------------------------------
# Step 8 — Health check + smoke tests
# ---------------------------------------------------------------------------
step "Step 8 / 8 — Health Check & Smoke Tests"

HEALTH_URL="http://localhost:${PORT}/health"
TIMEOUT=90
INTERVAL=3
ELAPSED=0

info "Waiting for health check at ${HEALTH_URL} (up to ${TIMEOUT}s)…"
until curl -sf "${HEALTH_URL}" >/dev/null 2>&1; do
  if [ "${ELAPSED}" -ge "${TIMEOUT}" ]; then
    error "Health check timed out after ${TIMEOUT}s."
    echo ""
    echo "  Debug:"
    echo "    ${DC} logs backend --tail 50"
    echo "    ${DC} ps"
    die "Service did not become healthy."
  fi
  sleep "${INTERVAL}"
  ELAPSED=$((ELAPSED + INTERVAL))
  printf "  ."
done
echo ""
ok "Health check passed (${ELAPSED}s)"

# Run smoke tests
if [ "${SKIP_SMOKE}" = "true" ]; then
  warn "Skipping smoke tests (--skip-smoke)"
elif [ -f "${REPO_ROOT}/scripts/smoke_api.py" ]; then
  info "Running API smoke tests…"
  if python3 "${REPO_ROOT}/scripts/smoke_api.py" --base-url "http://localhost:${PORT}"; then
    ok "Smoke tests passed"
  else
    warn "Smoke tests failed — review output above"
    warn "Services are running, but API behaviour may not be correct."
  fi
elif [ -f "${REPO_ROOT}/scripts/smoke_test.sh" ]; then
  info "Running bash smoke test…"
  bash "${REPO_ROOT}/scripts/smoke_test.sh" "http://localhost:${PORT}" && ok "Smoke tests passed" || warn "Smoke tests failed"
fi

# Optional full live verification
if [ "${VERIFY_LIVE}" = "true" ] && [ -f "${REPO_ROOT}/scripts/verify_live.py" ]; then
  info "Running full live environment verifier (--verify-live)…"
  python3 "${REPO_ROOT}/scripts/verify_live.py" --url "http://localhost:${PORT}" || warn "Live verification reported failures — review output"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}${GREEN}  SwarmEnterprise v2 — RUNNING  (${DURATION}s)${RESET}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${BOLD}API${RESET}       http://localhost:${PORT}"
echo -e "  ${BOLD}Docs${RESET}      http://localhost:${PORT}/docs"
echo -e "  ${BOLD}Health${RESET}    http://localhost:${PORT}/health"
echo -e "  ${BOLD}Metrics${RESET}   http://localhost:${PORT}/metrics"
echo -e "  ${BOLD}Profile${RESET}   ${DEPLOY_PROFILE}"
if [ "${DEPLOY_PROFILE}" = "production" ] && [ -n "${PRIMARY_DOMAIN:-}" ]; then
  echo -e "  ${BOLD}Public${RESET}    https://${PRIMARY_DOMAIN}"
fi
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Useful commands:"
echo "    ${DC} logs -f backend          # tail backend logs"
echo "    ${DC} ps                       # container status"
echo "    make health                    # health check"
echo "    make smoke                     # re-run smoke tests"
echo "    make verify-live               # full live verifier"
echo "    ./stop.sh                      # graceful shutdown"
echo ""
