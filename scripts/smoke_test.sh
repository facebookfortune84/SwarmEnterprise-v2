#!/usr/bin/env bash
# =============================================================================
# SwarmEnterprise v2 — Staging Smoke Test
#
# Usage:
#   ./scripts/smoke_test.sh [BASE_URL] [--verbose]
#
# Examples:
#   ./scripts/smoke_test.sh                            # defaults to http://localhost:8000
#   ./scripts/smoke_test.sh https://realms2riches.com
#   ./scripts/smoke_test.sh http://localhost:8000 --verbose
#
# Exit codes:
#   0 — all tests passed
#   1 — one or more tests failed
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
BASE_URL="http://localhost:8000"
VERBOSE=false

for arg in "$@"; do
  case "$arg" in
    --verbose|-v) VERBOSE=true ;;
    http://*|https://*) BASE_URL="$arg" ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

# Strip trailing slash for consistency
BASE_URL="${BASE_URL%/}"

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
AUTH_TOKEN=""

# ---------------------------------------------------------------------------
# Helper: run one curl test
#
#   check <label> <expected_http_code> [extra_grep_pattern] -- <curl args...>
#
# The '--' separator keeps curl args clearly separate from test args.
# ---------------------------------------------------------------------------
check() {
  local label="$1"
  local expected_code="$2"
  local body_pattern="${3:-}"
  shift 3
  # Consume '--' separator
  if [[ "${1:-}" == "--" ]]; then shift; fi

  local tmp
  tmp=$(mktemp)

  local actual_code
  actual_code=$(curl -s -o "$tmp" -w "%{http_code}" "$@") || true

  local body
  body=$(cat "$tmp")
  rm -f "$tmp"

  local ok=true

  if [[ "$actual_code" != "$expected_code" ]]; then
    ok=false
  fi

  if [[ -n "$body_pattern" && "$ok" == "true" ]]; then
    if ! echo "$body" | grep -q "$body_pattern"; then
      ok=false
    fi
  fi

  if [[ "$ok" == "true" ]]; then
    printf "${GREEN}[PASS]${RESET} %-55s  HTTP %s\n" "$label" "$actual_code"
    PASS=$((PASS + 1))
  else
    printf "${RED}[FAIL]${RESET} %-55s  HTTP %s (expected %s)\n" \
      "$label" "$actual_code" "$expected_code"
    FAIL=$((FAIL + 1))
  fi

  if [[ "$VERBOSE" == "true" ]]; then
    echo "       Body: $body"
    echo ""
  fi
}

# ---------------------------------------------------------------------------
# Helper: run curl and capture body + code (used for auth flow)
# ---------------------------------------------------------------------------
curl_json() {
  local url="$1"
  shift
  curl -s -w '\n%{http_code}' "$@" "$url"
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
printf "${CYAN}SwarmEnterprise v2 — Smoke Test${RESET}\n"
echo "Target: $BASE_URL"
echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "──────────────────────────────────────────────────────────────"

# ---------------------------------------------------------------------------
# 1. GET /health  →  200 + "status":"ONLINE"
# ---------------------------------------------------------------------------
check \
  "GET /health (200 + status:ONLINE)" \
  "200" \
  '"status"' \
  -- \
  -H "Accept: application/json" \
  "${BASE_URL}/health"

# Also assert the specific value (verbose shows body on failure)
TMP_HEALTH=$(mktemp)
HEALTH_CODE=$(curl -s -o "$TMP_HEALTH" -w "%{http_code}" -H "Accept: application/json" "${BASE_URL}/health") || true
HEALTH_BODY=$(cat "$TMP_HEALTH"); rm -f "$TMP_HEALTH"
if echo "$HEALTH_BODY" | grep -q '"ONLINE"'; then
  printf "${GREEN}[PASS]${RESET} %-55s  body ok\n" 'GET /health body contains "ONLINE"'
  PASS=$((PASS + 1))
else
  printf "${RED}[FAIL]${RESET} %-55s  got: %s\n" 'GET /health body contains "ONLINE"' "$HEALTH_BODY"
  FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# 2. GET /metrics  →  200
# ---------------------------------------------------------------------------
check \
  "GET /metrics (200)" \
  "200" \
  "" \
  -- \
  "${BASE_URL}/metrics"

# ---------------------------------------------------------------------------
# 3. GET /docs  →  200 (Swagger UI)
# ---------------------------------------------------------------------------
check \
  "GET /docs (Swagger UI, 200)" \
  "200" \
  "" \
  -- \
  "${BASE_URL}/docs"

# ---------------------------------------------------------------------------
# 4. POST /api/auth/register  →  201 (new smoke-test user)
# ---------------------------------------------------------------------------
SMOKE_EMAIL="smoke_$(date +%s)@test.invalid"
SMOKE_PASS="SmokePass#$(date +%s)"

REGISTER_TMP=$(mktemp)
REGISTER_CODE=$(curl -s -o "$REGISTER_TMP" -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${SMOKE_EMAIL}\",\"password\":\"${SMOKE_PASS}\",\"full_name\":\"Smoke Test\"}" \
  "${BASE_URL}/api/auth/register") || true
REGISTER_BODY=$(cat "$REGISTER_TMP"); rm -f "$REGISTER_TMP"

if [[ "$REGISTER_CODE" == "201" ]]; then
  printf "${GREEN}[PASS]${RESET} %-55s  HTTP %s\n" "POST /api/auth/register (201)" "$REGISTER_CODE"
  PASS=$((PASS + 1))
  # Extract access_token (portable; no jq required)
  AUTH_TOKEN=$(echo "$REGISTER_BODY" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
else
  printf "${RED}[FAIL]${RESET} %-55s  HTTP %s (expected 201)\n" "POST /api/auth/register (201)" "$REGISTER_CODE"
  FAIL=$((FAIL + 1))
fi

if [[ "$VERBOSE" == "true" ]]; then
  echo "       Body: $REGISTER_BODY"
  echo ""
fi

# ---------------------------------------------------------------------------
# 5. POST /api/auth/login  →  200 + access_token
# ---------------------------------------------------------------------------
LOGIN_TMP=$(mktemp)
LOGIN_CODE=$(curl -s -o "$LOGIN_TMP" -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${SMOKE_EMAIL}\",\"password\":\"${SMOKE_PASS}\"}" \
  "${BASE_URL}/api/auth/login") || true
LOGIN_BODY=$(cat "$LOGIN_TMP"); rm -f "$LOGIN_TMP"

if [[ "$LOGIN_CODE" == "200" ]]; then
  printf "${GREEN}[PASS]${RESET} %-55s  HTTP %s\n" "POST /api/auth/login (200)" "$LOGIN_CODE"
  PASS=$((PASS + 1))
  # Prefer login token if register token wasn't captured
  LOGIN_TOKEN=$(echo "$LOGIN_BODY" | grep -o '"access_token":"[^"]*"' | head -1 | cut -d'"' -f4)
  if [[ -n "$LOGIN_TOKEN" ]]; then AUTH_TOKEN="$LOGIN_TOKEN"; fi
  if echo "$LOGIN_BODY" | grep -q '"access_token"'; then
    printf "${GREEN}[PASS]${RESET} %-55s  token present\n" "POST /api/auth/login body contains access_token"
    PASS=$((PASS + 1))
  else
    printf "${RED}[FAIL]${RESET} %-55s  token missing in body\n" "POST /api/auth/login body contains access_token"
    FAIL=$((FAIL + 1))
  fi
else
  printf "${RED}[FAIL]${RESET} %-55s  HTTP %s (expected 200)\n" "POST /api/auth/login (200)" "$LOGIN_CODE"
  FAIL=$((FAIL + 1))
  printf "${RED}[FAIL]${RESET} %-55s  (login failed, skipped)\n" "POST /api/auth/login body contains access_token"
  FAIL=$((FAIL + 1))
fi

if [[ "$VERBOSE" == "true" ]]; then
  echo "       Body: $LOGIN_BODY"
  echo ""
fi

# ---------------------------------------------------------------------------
# 6. GET /api/companies  →  200  (authenticated)
# ---------------------------------------------------------------------------
if [[ -n "$AUTH_TOKEN" ]]; then
  check \
    "GET /api/companies/ (200, authenticated)" \
    "200" \
    "" \
    -- \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    "${BASE_URL}/api/companies/"
else
  printf "${RED}[FAIL]${RESET} %-55s  (skipped — no auth token)\n" "GET /api/companies/ (200, authenticated)"
  FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# 7. GET /api/stripe/create-checkout-session  →  405 Method Not Allowed
#    (the endpoint exists as POST; a GET proves routing is live)
# ---------------------------------------------------------------------------
check \
  "GET /api/stripe/create-checkout-session (405, route exists)" \
  "405" \
  "" \
  -- \
  "${BASE_URL}/api/stripe/create-checkout-session"

# ---------------------------------------------------------------------------
# 8. GET /api/auth/verify  →  401 (proves auth guard is active)
# ---------------------------------------------------------------------------
check \
  "GET /api/auth/verify (401 without token)" \
  "401" \
  "" \
  -- \
  "${BASE_URL}/api/auth/verify"

# ---------------------------------------------------------------------------
# 9. HTTPS check (only when BASE_URL is https://)
# ---------------------------------------------------------------------------
if [[ "$BASE_URL" == https://* ]]; then
  HTTPS_TMP=$(mktemp)
  HTTPS_CODE=$(curl -s -o "$HTTPS_TMP" -w "%{http_code}" \
    -I --max-time 10 \
    "${BASE_URL}/health") || true
  HTTPS_BODY=$(cat "$HTTPS_TMP"); rm -f "$HTTPS_TMP"

  if [[ "$HTTPS_CODE" == "200" ]]; then
    printf "${GREEN}[PASS]${RESET} %-55s  HTTP %s\n" "HTTPS TLS check (200)" "$HTTPS_CODE"
    PASS=$((PASS + 1))
  else
    printf "${RED}[FAIL]${RESET} %-55s  HTTP %s (expected 200)\n" "HTTPS TLS check (200)" "$HTTPS_CODE"
    FAIL=$((FAIL + 1))
  fi

  if [[ "$VERBOSE" == "true" ]]; then
    echo "       Headers: $HTTPS_BODY"
    echo ""
  fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "──────────────────────────────────────────────────────────────"
TOTAL=$((PASS + FAIL))
printf "Results: ${GREEN}%d passed${RESET} / ${RED}%d failed${RESET} / %d total\n" \
  "$PASS" "$FAIL" "$TOTAL"
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  printf "${RED}SMOKE TEST FAILED${RESET}\n"
  exit 1
fi

printf "${GREEN}SMOKE TEST PASSED${RESET}\n"
exit 0
