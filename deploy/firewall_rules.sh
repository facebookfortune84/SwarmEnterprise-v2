#!/usr/bin/env bash
# UFW firewall rules for SwarmEnterprise production server
# Run as root/sudo: sudo bash deploy/firewall_rules.sh
#
# Allows : 80, 443 from any          (public web traffic via Caddy)
# Allows : 22 SSH only from ADMIN_CIDR (default: set ADMIN_CIDR env var before running)
# Blocks : 3000  (Grafana)           — internal only, access via WireGuard or SSH tunnel
# Blocks : 9090  (Prometheus)        — internal only
# Blocks : 9093  (Alertmanager)      — internal only
# Blocks : 8000  (backend)           — internal only, fronted by Caddy
# Blocks : 5432  (PostgreSQL)        — internal only
# Blocks : 6379  (Redis)             — internal only
# Blocks : 9000/9001 (MinIO)         — internal only
# Blocks : 3100  (Loki)              — internal only
# Blocks : 8001  (ChromaDB)          — internal only
# Enables: UFW

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Set ADMIN_CIDR to your admin IP or CIDR block before running.
# Examples:
#   ADMIN_CIDR=203.0.113.42/32 sudo bash deploy/firewall_rules.sh
#   ADMIN_CIDR=10.8.0.0/24     sudo bash deploy/firewall_rules.sh  (WireGuard subnet)
ADMIN_CIDR="${ADMIN_CIDR:-}"

if [[ -z "$ADMIN_CIDR" ]]; then
  echo "ERROR: ADMIN_CIDR is not set."
  echo "Usage: ADMIN_CIDR=<your-ip>/32 sudo bash deploy/firewall_rules.sh"
  echo "       ADMIN_CIDR=10.8.0.0/24  sudo bash deploy/firewall_rules.sh"
  exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: This script must be run as root (or with sudo)."
  exit 1
fi

echo "=== SwarmEnterprise UFW Hardening ==="
echo "Admin CIDR : ${ADMIN_CIDR}"
echo ""

# ---------------------------------------------------------------------------
# Reset to a clean state
# ---------------------------------------------------------------------------
ufw --force reset

# Default policies: deny all incoming, allow all outgoing
ufw default deny incoming
ufw default allow outgoing

# ---------------------------------------------------------------------------
# SSH — restricted to admin CIDR only
# ---------------------------------------------------------------------------
echo "[+] Allowing SSH (22) from ${ADMIN_CIDR} only"
ufw allow from "${ADMIN_CIDR}" to any port 22 proto tcp comment 'SSH admin access'

# ---------------------------------------------------------------------------
# Public web traffic — Caddy handles TLS termination
# ---------------------------------------------------------------------------
echo "[+] Allowing HTTP (80) from any"
ufw allow 80/tcp comment 'HTTP (redirected to HTTPS by Caddy)'

echo "[+] Allowing HTTPS (443 TCP+UDP) from any"
ufw allow 443/tcp comment 'HTTPS'
ufw allow 443/udp comment 'HTTPS HTTP/3 QUIC'

# ---------------------------------------------------------------------------
# Block monitoring / internal services from external access
# These ports are only reachable via WireGuard VPN or SSH tunnels.
# UFW rules below are belt-and-suspenders for when Docker host-port bindings
# are inadvertently set (Docker manipulates iptables directly, so prefer
# binding these services to 127.0.0.1 in docker-compose; see SECURITY_HARDENING.md).
# ---------------------------------------------------------------------------
echo "[+] Blocking external access to internal service ports"

# Backend API — served exclusively through Caddy
ufw deny 8000/tcp  comment 'backend — internal, behind Caddy'

# Prometheus
ufw deny 9090/tcp  comment 'Prometheus — internal monitoring'

# Alertmanager
ufw deny 9093/tcp  comment 'Alertmanager — internal monitoring'

# Grafana
ufw deny 3000/tcp  comment 'Grafana — internal monitoring'

# Loki
ufw deny 3100/tcp  comment 'Loki — internal log aggregation'

# PostgreSQL
ufw deny 5432/tcp  comment 'PostgreSQL — internal database'

# Redis
ufw deny 6379/tcp  comment 'Redis — internal cache/queue'

# MinIO API + Console
ufw deny 9000/tcp  comment 'MinIO API — internal object storage'
ufw deny 9001/tcp  comment 'MinIO Console — internal'

# ChromaDB
ufw deny 8001/tcp  comment 'ChromaDB — internal vector store'

# ---------------------------------------------------------------------------
# Enable UFW
# ---------------------------------------------------------------------------
echo "[+] Enabling UFW"
ufw --force enable

echo ""
echo "=== Final ruleset ==="
ufw status verbose

echo ""
echo "Done. UFW is active."
echo "To monitor blocked traffic: journalctl -f -k | grep 'UFW BLOCK'"
