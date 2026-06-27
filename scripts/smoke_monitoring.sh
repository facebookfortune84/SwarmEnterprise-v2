#!/usr/bin/env bash
# =============================================================================
# SwarmEnterprise v2 — Monitoring Stack Smoke Test
#
# Usage:
#   ./scripts/smoke_monitoring.sh [BASE_URL]
#   ./scripts/smoke_monitoring.sh --help
#
# Arguments:
#   BASE_URL   Base URL of the SwarmOS backend (default: http://localhost:8000)
#
# Examples:
#   ./scripts/smoke_monitoring.sh
#   ./scripts/smoke_monitoring.sh http://localhost:8000
#   ./scripts/smoke_monitoring.sh https://realms2riches.com
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
# =============================================================================
set -uo pipefail

# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------
for arg in "$@"; do
  if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
    sed -n '2,18p' "$0" | sed 's/^# \?//'
    exit 0
  fi
done

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"   # strip trailing slash

# ---------------------------------------------------------------------------
# Colour helpers (disabled when not a TTY)
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  GREEN='\033[0;32m'
  RED='\033[0;31m'
  CYAN='\033[0;36m'
  RESET='\033[0m'
else
  GREEN='' RED='' CYAN='' RESET=''
fi

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helper: check <label> <url> <expected_http_code> [body_pattern]
#
#   Curls the URL, asserts the HTTP status code equals expected_http_code.
#   If body_pattern is provided, also asserts it appears in the response body.
#   Prints [PASS] or [FAIL] with the actual HTTP status code.
# ---------------------------------------------------------------------------
check() {
  local label="$1"
  local url="$2"
  local expected_code="$3"
  local body_pattern="${4:-}"

  local tmp
  tmp=$(mktemp)

  local actual_code
  actual_code=$(curl -s -o "$tmp" -w "%{http_code}" --max-time 10 "$url") || actual_code="000"

  local body
  body=$(cat "$tmp")
  rm -f "$tmp"

  local ok=true

  if [[ "$actual_code" != "$expected_code" ]]; then
    ok=false
  fi

  if [[ -n "$body_pattern" && "$ok" == "true" ]]; then
    if ! echo "$body" | grep -qF "$body_pattern"; then
      ok=false
    fi
  fi

  if [[ "$ok" == "true" ]]; then
    printf "${GREEN}[PASS]${RESET} %-60s  HTTP %s\n" "$label" "$actual_code"
    PASS=$((PASS + 1))
  else
    if [[ -n "$body_pattern" && "$actual_code" == "$expected_code" ]]; then
      printf "${RED}[FAIL]${RESET} %-60s  HTTP %s (body pattern '%s' not found)\n" \
        "$label" "$actual_code" "$body_pattern"
    else
      printf "${RED}[FAIL]${RESET} %-60s  HTTP %s (expected %s)\n" \
        "$label" "$actual_code" "$expected_code"
    fi
    FAIL=$((FAIL + 1))
  fi
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
printf "${CYAN}SwarmEnterprise v2 — Monitoring Smoke Test${RESET}\n"
echo "Backend: $BASE_URL"
echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "────────────────────────────────────────────────────────────────────"

# ---------------------------------------------------------------------------
# 1. Backend — /health  →  200 + body contains "ONLINE"
# ---------------------------------------------------------------------------
check \
  "Backend  GET /health (200, body: \"ONLINE\")" \
  "${BASE_URL}/health" \
  "200" \
  "ONLINE"

# ---------------------------------------------------------------------------
# 2. Backend — /metrics  →  200 + Prometheus text format (# HELP)
# ---------------------------------------------------------------------------
check \
  "Backend  GET /metrics (200, body: \"# HELP\")" \
  "${BASE_URL}/metrics" \
  "200" \
  "# HELP"

# ---------------------------------------------------------------------------
# 3. Prometheus — /-/healthy  →  200
# ---------------------------------------------------------------------------
check \
  "Prometheus  GET /-/healthy (200)" \
  "http://localhost:9090/-/healthy" \
  "200"

# ---------------------------------------------------------------------------
# 4. Prometheus — /-/ready  →  200
# ---------------------------------------------------------------------------
check \
  "Prometheus  GET /-/ready (200)" \
  "http://localhost:9090/-/ready" \
  "200"

# ---------------------------------------------------------------------------
# 5. Grafana — /api/health  →  200
# ---------------------------------------------------------------------------
check \
  "Grafana     GET /api/health (200)" \
  "http://localhost:3000/api/health" \
  "200"

# ---------------------------------------------------------------------------
# 6. Loki — /ready  →  200
# ---------------------------------------------------------------------------
check \
  "Loki        GET /ready (200)" \
  "http://localhost:3100/ready" \
  "200"

# ---------------------------------------------------------------------------
# 7. Alertmanager — /-/healthy  →  200
# ---------------------------------------------------------------------------
check \
  "Alertmanager GET /-/healthy (200)" \
  "http://localhost:9093/-/healthy" \
  "200"

# ---------------------------------------------------------------------------
# 8. Node Exporter — /metrics  →  200
# ---------------------------------------------------------------------------
check \
  "node-exporter GET /metrics (200)" \
  "http://localhost:9100/metrics" \
  "200"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "────────────────────────────────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
printf "Results: ${GREEN}%d passed${RESET} / ${RED}%d failed${RESET} / %d total\n" \
  "$PASS" "$FAIL" "$TOTAL"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  printf "${RED}MONITORING SMOKE TEST FAILED${RESET}\n"
  exit 1
fi

printf "${GREEN}MONITORING SMOKE TEST PASSED${RESET}\n"
exit 0
