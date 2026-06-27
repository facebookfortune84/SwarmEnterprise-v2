#!/usr/bin/env bash
# stop.sh — SwarmEnterprise v2 graceful shutdown
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

DRAIN_TIMEOUT=15
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# Resolve compose command
# ---------------------------------------------------------------------------
if command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  DC="docker compose"
else
  error "'docker compose' not found — cannot shut down containers."
  DC="docker compose"  # attempt anyway
fi

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${YELLOW}${BOLD}  SwarmEnterprise v2 — STOPPING${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# ---------------------------------------------------------------------------
# Step 1 — Send SIGTERM to running backend process (inside container) so
#           FastAPI shutdown events fire (connection draining, Celery flush).
# ---------------------------------------------------------------------------
info "Sending SIGTERM to backend container …"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "swarmOS-backend"; then
  docker kill --signal=SIGTERM swarmOS-backend 2>/dev/null || warn "Could not signal backend container."
else
  warn "swarmOS-backend container not found — may already be stopped."
fi

# Also signal the worker if present
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "swarmOS-worker"; then
  docker kill --signal=SIGTERM swarmOS-worker 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# Step 2 — Wait for connections to drain
# ---------------------------------------------------------------------------
info "Waiting ${DRAIN_TIMEOUT}s for connections to drain …"
sleep "${DRAIN_TIMEOUT}"

# ---------------------------------------------------------------------------
# Step 3 — docker compose down (removes containers; volumes are preserved)
# ---------------------------------------------------------------------------
info "Running docker compose down …"
(cd "${REPO_ROOT}" && ${DC} down --remove-orphans) || warn "docker compose down reported an error (non-fatal)."

# ---------------------------------------------------------------------------
# Step 4 — Confirm
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  SwarmEnterprise v2 — STOPPED${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  All containers stopped. Volumes and networks preserved."
echo "  To restart: ./start.sh  or  make launch"
echo ""
