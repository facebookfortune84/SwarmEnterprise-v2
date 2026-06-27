#!/usr/bin/env bash
# scripts/security_audit.sh — SwarmEnterprise production security audit
#
# Usage:  sudo bash scripts/security_audit.sh
#
# Checks:
#   1. SSH PasswordAuthentication is disabled
#   2. UFW is active
#   3. Docker daemon is NOT listening on TCP
#   4. No plaintext secrets committed to git history
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS=0
FAIL=0

pass() { echo "  [PASS] $*"; ((PASS++)) || true; }
fail() { echo "  [FAIL] $*"; ((FAIL++)) || true; }

section() { echo ""; echo "=== $* ==="; }

# ---------------------------------------------------------------------------
# Check 1 — SSH: PasswordAuthentication is no
# ---------------------------------------------------------------------------
section "1. SSH PasswordAuthentication"

# sshd -T renders the full effective configuration (merges all drop-ins).
# We check both key spellings; OpenSSH normalises to lowercase.
if command -v sshd &>/dev/null; then
  pa_value=$(sshd -T 2>/dev/null | awk '/^passwordauthentication / { print tolower($2) }')
  if [[ "$pa_value" == "no" ]]; then
    pass "PasswordAuthentication is 'no'"
  elif [[ -z "$pa_value" ]]; then
    fail "Could not determine PasswordAuthentication value (run as root?)"
  else
    fail "PasswordAuthentication is '${pa_value}' — expected 'no'"
  fi
else
  fail "sshd binary not found — is OpenSSH server installed?"
fi

# ---------------------------------------------------------------------------
# Check 2 — UFW is active
# ---------------------------------------------------------------------------
section "2. UFW firewall status"

if command -v ufw &>/dev/null; then
  ufw_status=$(ufw status 2>/dev/null | head -1)
  if echo "$ufw_status" | grep -qi "Status: active"; then
    pass "UFW is active"
    # Bonus: warn if port 22 is open to the world
    if ufw status 2>/dev/null | grep -qE "^22(/tcp)?\s+ALLOW\s+Anywhere"; then
      echo "  [WARN] SSH port 22 is open to Anywhere — consider restricting to ADMIN_CIDR"
    fi
  else
    fail "UFW is not active (status: ${ufw_status})"
  fi
else
  fail "ufw not found — install with: apt install ufw"
fi

# ---------------------------------------------------------------------------
# Check 3 — Docker daemon is not listening on TCP
# ---------------------------------------------------------------------------
section "3. Docker daemon TCP socket"

tcp_exposed=false

# Method A: check daemon.json for tcp:// hosts
daemon_json="/etc/docker/daemon.json"
if [[ -f "$daemon_json" ]]; then
  if grep -q '"tcp://' "$daemon_json" 2>/dev/null; then
    fail "daemon.json contains a tcp:// host entry — remove it"
    tcp_exposed=true
  fi
fi

# Method B: check listening sockets on 2375 and 2376
for port in 2375 2376; do
  if ss -tlnp 2>/dev/null | grep -q ":${port}[[:space:]]"; then
    fail "Docker is listening on TCP port ${port} — this is a critical exposure"
    tcp_exposed=true
  fi
done

# Method C: check dockerd process arguments
if pgrep -a dockerd 2>/dev/null | grep -q -- '-H tcp://'; then
  fail "dockerd is running with a -H tcp:// flag — remove it from the service unit"
  tcp_exposed=true
fi

if [[ "$tcp_exposed" == "false" ]]; then
  pass "Docker daemon is not exposed on TCP"
fi

# ---------------------------------------------------------------------------
# Check 4 — No plaintext secrets in git log
# ---------------------------------------------------------------------------
section "4. Plaintext secrets in git history"

if ! command -v git &>/dev/null; then
  fail "git not found — cannot scan history"
else
  # Patterns that indicate plaintext secrets.
  # Intentionally limited to high-signal patterns to reduce false positives.
  SECRET_PATTERNS=(
    'password\s*=\s*["\047][^"'\'']{6,}'   # password = "..."  or  password = '...'
    'secret\s*=\s*["\047][^"'\'']{8,}'      # secret = "..."
    'api_key\s*=\s*["\047][^"'\'']{8,}'     # api_key = "..."
    'JWT_SECRET\s*=\s*[^$\s]{8,}'           # JWT_SECRET=<literal>
    'POSTGRES_PASSWORD\s*=\s*[^$\s]{4,}'    # POSTGRES_PASSWORD=<literal>
    'MINIO_SECRET_KEY\s*=\s*[^$\s]{8,}'     # MINIO_SECRET_KEY=<literal>
    'GRAFANA_PASSWORD\s*=\s*[^$\s]{4,}'     # GRAFANA_PASSWORD=<literal>
    'BEGIN\s+(RSA|OPENSSH|EC)\s+PRIVATE KEY' # Private key material
    'ghp_[A-Za-z0-9]{36}'                   # GitHub personal access token
    'sk-[A-Za-z0-9]{48}'                    # OpenAI API key
  )

  found_secrets=false

  for pattern in "${SECRET_PATTERNS[@]}"; do
    # Search the full git log output (diff context only) for the pattern
    matches=$(git log --all -p --no-color 2>/dev/null \
                | grep -iE "$pattern" \
                | grep -v '^---' \
                | grep -v '^\+\+\+' \
                | grep '^\+' \
              || true)

    if [[ -n "$matches" ]]; then
      fail "Potential secret pattern '${pattern}' found in git history"
      # Print up to 3 matching lines for context (truncated for safety)
      echo "$matches" | head -3 | sed 's/./*/4g' | while IFS= read -r line; do
        echo "         hint: ${line:0:120}"
      done
      found_secrets=true
    fi
  done

  if [[ "$found_secrets" == "false" ]]; then
    pass "No plaintext secret patterns detected in git history"
  fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=============================="
echo " Audit complete"
echo " PASS: ${PASS}   FAIL: ${FAIL}"
echo "=============================="
echo ""

if [[ "$FAIL" -gt 0 ]]; then
  echo "Action required: remediate all FAIL items before deploying to production."
  echo "See docs/guides/SECURITY_HARDENING.md for remediation steps."
  exit 1
fi

exit 0
