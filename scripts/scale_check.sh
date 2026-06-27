#!/usr/bin/env bash
# scale_check.sh — Pre-flight checks for a horizontally scaled SwarmEnterprise backend.
# Each check prints PASS or FAIL with a short reason, then exits non-zero if any failed.
#
# Usage:
#   bash scripts/scale_check.sh
#   BACKEND_URL=http://localhost:8000 bash scripts/scale_check.sh
set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS=0
FAIL=0

pass() { echo "  PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL  $1"; FAIL=$((FAIL + 1)); }

section() { echo; echo "── $1"; }

# ---------------------------------------------------------------------------
# Check 1: REDIS_URL is set and non-empty
# ---------------------------------------------------------------------------
section "Redis configuration"
if [ -z "${REDIS_URL:-}" ]; then
    fail "REDIS_URL is not set — JWT revocation blocklist will not work"
else
    pass "REDIS_URL is set: ${REDIS_URL}"
fi

# ---------------------------------------------------------------------------
# Check 2: DATABASE_URL is set and does NOT point to localhost / 127.x
# ---------------------------------------------------------------------------
section "Database configuration"
if [ -z "${DATABASE_URL:-}" ]; then
    fail "DATABASE_URL is not set"
else
    # Strip scheme so we can inspect the host portion
    db_host=$(echo "${DATABASE_URL}" | sed -E 's|^[^/]+//([^:/]+).*|\1|')
    if [[ "${db_host}" == "localhost" || "${db_host}" =~ ^127\. ]]; then
        fail "DATABASE_URL points to '${db_host}' — must point to an external/shared host at scale"
    else
        pass "DATABASE_URL points to external host: ${db_host}"
    fi
fi

# ---------------------------------------------------------------------------
# Check 3: No in-memory session files in /tmp
#   Flask/Werkzeug and some other frameworks write session pickles to /tmp.
#   If any exist, this instance is carrying per-process state.
# ---------------------------------------------------------------------------
section "In-memory session files"
session_files=$(find /tmp -maxdepth 2 -name "*.session" -o -name "flask_session_*" 2>/dev/null | head -5 || true)
if [ -n "${session_files}" ]; then
    fail "Found per-process session files in /tmp — these are not shared across replicas:"
    echo "${session_files}" | while read -r f; do echo "        $f"; done
else
    pass "No in-memory session files found in /tmp"
fi

# ---------------------------------------------------------------------------
# Check 4: Backend health endpoint returns HTTP 200
# ---------------------------------------------------------------------------
section "Backend health endpoint"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
HEALTH_URL="${BACKEND_URL%/}/health"

if ! command -v curl &>/dev/null; then
    fail "curl not found — cannot check health endpoint"
else
    http_code=$(curl --silent --output /dev/null --write-out "%{http_code}" \
        --max-time 5 "${HEALTH_URL}" || echo "000")
    if [ "${http_code}" = "200" ]; then
        pass "GET ${HEALTH_URL} returned HTTP 200"
    else
        fail "GET ${HEALTH_URL} returned HTTP ${http_code} (expected 200)"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo
echo "────────────────────────────────────────"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "────────────────────────────────────────"

if [ "${FAIL}" -gt 0 ]; then
    exit 1
fi
