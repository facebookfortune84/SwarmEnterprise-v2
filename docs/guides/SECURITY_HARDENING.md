# Security Hardening Guide — SwarmEnterprise v2

> **Audience:** Server administrators deploying SwarmEnterprise to a production VPS or bare-metal host.  
> **Applies to:** Ubuntu 22.04 LTS / Debian 12 running Docker Compose with the `deploy/docker/docker-compose.production-*.yml` overlay.

---

## Table of Contents

1. [Firewall Setup (UFW)](#1-firewall-setup-ufw)
2. [SSH Key Deployment & Hardening](#2-ssh-key-deployment--hardening)
3. [VPN for Admin / Monitoring Access (WireGuard)](#3-vpn-for-admin--monitoring-access-wireguard)
4. [DDoS Protection via Cloudflare](#4-ddos-protection-via-cloudflare)
5. [Docker Daemon Security](#5-docker-daemon-security)
6. [Security Update Policy](#6-security-update-policy)

---

## 1. Firewall Setup (UFW)

### Port inventory

| Port(s) | Service | Exposure |
|---------|---------|----------|
| 80 / 443 | Caddy (HTTP + HTTPS) | ✅ Public |
| 443/udp | Caddy HTTP/3 (QUIC) | ✅ Public |
| 22 | SSH | ⚠️ Admin CIDR only |
| 51820/udp | WireGuard VPN | ⚠️ Admin CIDR only |
| 8000 | Backend (FastAPI) | 🔒 Internal — behind Caddy |
| 3000 | Grafana | 🔒 Internal — WireGuard/tunnel only |
| 9090 | Prometheus | 🔒 Internal — WireGuard/tunnel only |
| 9093 | Alertmanager | 🔒 Internal — WireGuard/tunnel only |
| 3100 | Loki | 🔒 Internal |
| 5432 | PostgreSQL | 🔒 Internal |
| 6379 | Redis | 🔒 Internal |
| 9000 / 9001 | MinIO API / Console | 🔒 Internal |
| 8001 | ChromaDB | 🔒 Internal |

### Prerequisites

- Ubuntu 22.04+ or Debian 12+ with `ufw` installed (`apt install ufw`)
- Your admin IP address or CIDR block (e.g. `203.0.113.42/32` or a WireGuard subnet `10.8.0.0/24`)

### Running `firewall_rules.sh`

```bash
# 1. Set your admin CIDR (replace with your actual IP/block)
export ADMIN_CIDR="203.0.113.42/32"

# 2. Run the script as root
sudo -E bash deploy/firewall_rules.sh
```

The script:

1. Resets UFW to a clean state.
2. Sets default policy to `deny incoming`, `allow outgoing`.
3. Allows SSH **only** from `ADMIN_CIDR`.
4. Allows ports 80 and 443 (TCP + UDP) from anywhere.
5. Explicitly denies all internal service ports listed above.
6. Enables UFW.

> **⚠️ Important — Docker iptables bypass:** Docker directly inserts iptables rules that can bypass UFW's `INPUT` chain for host-port bindings. The most reliable mitigation is to bind internal services to `127.0.0.1` in Docker Compose (e.g. `"127.0.0.1:9090:9090"` instead of `"9090:9090"`). The UFW deny rules in `firewall_rules.sh` serve as belt-and-suspenders but should not be relied upon as the sole control. See [Docker's documentation](https://docs.docker.com/network/iptables/) for full details.

### Verify the ruleset

```bash
sudo ufw status verbose

# Monitor blocked traffic in real time
sudo journalctl -f -k | grep 'UFW BLOCK'
```

### Allowing WireGuard (once VPN is configured — see §3)

```bash
export ADMIN_CIDR="<your-public-ip>/32"
sudo ufw allow from "${ADMIN_CIDR}" to any port 51820 proto udp comment 'WireGuard VPN'
```

---

## 2. SSH Key Deployment & Hardening

### Step 1 — Generate a deploy keypair (on your workstation)

```bash
# Ed25519 is preferred over RSA for new keys
ssh-keygen -t ed25519 -C "swarmenterprise-deploy-$(date +%Y%m%d)" \
           -f ~/.ssh/swarmenterprise_deploy

# Display the public key to copy to the server
cat ~/.ssh/swarmenterprise_deploy.pub
```

### Step 2 — Install the public key on the server

```bash
# From your workstation (server must still accept passwords or
# you must have another authorized key to bootstrap):
ssh-copy-id -i ~/.ssh/swarmenterprise_deploy.pub deploy@<server-ip>

# Or manually on the server:
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "<paste public key here>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 3 — Deploy the SSH hardening drop-in

```bash
# Copy the drop-in config to the server
sudo cp deploy/ssh_hardening.conf /etc/ssh/sshd_config.d/99-swarmenterprise.conf
sudo chmod 644 /etc/ssh/sshd_config.d/99-swarmenterprise.conf

# (Optional) Create the login banner
sudo tee /etc/ssh/swarmenterprise_banner <<'EOF'
******************************************************************
* Authorized access only. All activity is logged and monitored. *
* Disconnect immediately if you are not an authorized user.     *
******************************************************************
EOF
sudo chmod 644 /etc/ssh/swarmenterprise_banner

# Validate the configuration before reloading
sudo sshd -t && echo "Config OK"

# Reload sshd (does NOT drop existing sessions)
sudo systemctl reload sshd
```

> **⚠️ Test before closing your current session.** Open a **new** terminal and verify you can SSH in with your key before the old password-auth session times out.

### Step 4 — Add the deploy key to CI/CD

For GitHub Actions, add the private key as a repository secret (`SSH_DEPLOY_KEY`) and use it with `ssh-agent`:

```yaml
- uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.SSH_DEPLOY_KEY }}
```

### SSH hardening summary

| Setting | Value | Rationale |
|---------|-------|-----------|
| `PasswordAuthentication` | `no` | Eliminates brute-force password attacks |
| `PermitRootLogin` | `no` | Forces use of a named deploy account |
| `AuthenticationMethods` | `publickey` | Only Ed25519/RSA keys accepted |
| `MaxAuthTries` | `3` | Limits automated probing |
| `LoginGraceTime` | `20` | Reduces unauthenticated connection window |
| `X11Forwarding` | `no` | No GUI tunnelling needed on a server |
| `AllowAgentForwarding` | `no` | Prevents credential theft via forwarded agent |
| `AllowTcpForwarding` | `no` | Disables arbitrary TCP tunnels |
| `ClientAliveInterval` | `300` | Keepalive every 5 min |
| `ClientAliveCountMax` | `3` | Disconnect after 3 missed replies |

---

## 3. VPN for Admin / Monitoring Access (WireGuard)

Prometheus (9090), Grafana (3000), Alertmanager (9093), and other internal services must **never** be directly reachable from the public internet. The recommended approach is a WireGuard tunnel so admin traffic arrives on a private interface.

### Install WireGuard (server)

```bash
sudo apt update && sudo apt install -y wireguard

# Generate server keypair
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
sudo chmod 600 /etc/wireguard/server_private.key

cat /etc/wireguard/server_public.key   # share with admin peers
```

### Minimal `/etc/wireguard/wg0.conf` (server)

```ini
[Interface]
Address    = 10.8.0.1/24
ListenPort = 51820
PrivateKey = <server_private_key>

# Admin peer 1 — replace with admin's public key and allowed IP
[Peer]
PublicKey  = <admin_public_key>
AllowedIPs = 10.8.0.2/32
```

```bash
sudo systemctl enable --now wg-quick@wg0
```

### Admin workstation peer config

```ini
[Interface]
Address    = 10.8.0.2/24
PrivateKey = <admin_private_key>

[Peer]
PublicKey  = <server_public_key>
Endpoint   = <server-public-ip>:51820
AllowedIPs = 10.8.0.0/24   # route only the VPN subnet through the tunnel
PersistentKeepalive = 25
```

### Access monitoring over WireGuard

Once connected to the VPN, monitoring services are reachable at their Docker-bound `127.0.0.1` addresses via the WireGuard gateway, **or** bind them to `10.8.0.1` explicitly:

```bash
# After VPN is up, SSH tunnel approach (alternative to full VPN routing)
ssh -L 3000:localhost:3000 \
    -L 9090:localhost:9090 \
    -L 9093:localhost:9093 \
    deploy@<server-ip>
# Then browse: http://localhost:3000  (Grafana)
#              http://localhost:9090  (Prometheus)
```

### Open WireGuard in the firewall

```bash
# Only allow from known admin IPs; use 'any' if admin IP is dynamic
sudo ufw allow from "${ADMIN_CIDR}" to any port 51820 proto udp comment 'WireGuard'
```

---

## 4. DDoS Protection via Cloudflare

### Architecture

```
Internet  ──►  Cloudflare (orange-cloud)  ──►  Caddy (443)  ──►  Backend (8000)
```

All DNS A/AAAA records for `realms2riches.com`, `api.realms2riches.com`, `corp.realms2riches.com`, and `*.realms2riches.tech` must be **orange-clouded** (proxied) in the Cloudflare dashboard. This hides the origin IP and routes all traffic through Cloudflare's anycast network.

### Step 1 — Enable Cloudflare proxy ("orange-cloud")

In the Cloudflare DNS dashboard:

1. Set record type to `A`, value to your server's public IP.
2. Toggle **Proxy status** to **Proxied** (orange cloud icon).
3. Repeat for every subdomain that should be publicly accessible.

Do **not** orange-cloud records used only internally (e.g. WireGuard endpoint if you use a separate hostname for it).

### Step 2 — Restrict Caddy to Cloudflare IPs only

This ensures that traffic bypassing Cloudflare is rejected at the Caddy level. Add the following to the global block in `deploy/Caddyfile.self-hosted`:

```caddy
{
    # ... existing options ...

    # Accept connections only from Cloudflare's published IP ranges.
    # Fetch latest ranges: https://www.cloudflare.com/ips/
    servers {
        trusted_proxies static \
            173.245.48.0/20 \
            103.21.244.0/22 \
            103.22.200.0/22 \
            103.31.4.0/22 \
            141.101.64.0/18 \
            108.162.192.0/18 \
            190.93.240.0/20 \
            188.114.96.0/20 \
            197.234.240.0/22 \
            198.41.128.0/17 \
            162.158.0.0/15 \
            104.16.0.0/13 \
            104.24.0.0/14 \
            172.64.0.0/13 \
            131.0.72.0/22 \
            2400:cb00::/32 \
            2606:4700::/32 \
            2803:f800::/32 \
            2405:b500::/32 \
            2405:8100::/32 \
            2a06:98c0::/29 \
            2c0f:f248::/32
    }
}
```

Then add a catch-all to reject non-Cloudflare traffic by source IP using a Caddy `@notCloudflare` matcher in each virtual host, or use an upstream firewall rule (UFW / iptables) to only accept port 80/443 from [Cloudflare's published IP list](https://www.cloudflare.com/ips/).

### Step 3 — Enable Cloudflare WAF & DDoS rules

In the Cloudflare dashboard for `realms2riches.com`:

| Setting | Recommended value |
|---------|-------------------|
| **Security Level** | Medium or High |
| **DDoS protection** | Enabled (automatic — all plans) |
| **Bot Fight Mode** | Enabled (free plan) |
| **WAF Managed Ruleset** | Enable OWASP Core, Cloudflare Managed Rules |
| **Rate Limiting** | 100 req/10s per IP on `/api/*` |
| **Under Attack Mode** | Enable manually during active attacks |

### Step 4 — SSL/TLS mode

Set Cloudflare SSL/TLS mode to **Full (Strict)** to validate Caddy's Let's Encrypt certificate end-to-end. This prevents SSL stripping between Cloudflare and your origin.

### Step 5 — Authenticated Origin Pulls

Enable **Authenticated Origin Pulls** in Cloudflare (requires a client certificate on Caddy). This guarantees that even if your origin IP leaks, Cloudflare's certificate is required to reach Caddy:

```caddy
api.realms2riches.com {
    tls {
        client_auth {
            mode require_and_verify
            trusted_ca_cert_file /etc/caddy/cloudflare-origin-pull-ca.pem
        }
    }
    # ... rest of config
}
```

Download the CA cert from: `https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem`

---

## 5. Docker Daemon Security

### Never expose the Docker TCP socket

The Docker daemon **must** communicate via the Unix socket only. Exposing `tcp://0.0.0.0:2375` or `tcp://0.0.0.0:2376` effectively grants root access to anyone who can reach it.

**Verify the daemon is not listening on TCP:**

```bash
sudo ss -tlnp | grep 2375
sudo ss -tlnp | grep 2376
# Both should return nothing

# Also check the daemon config
cat /etc/docker/daemon.json
```

Ensure `/etc/docker/daemon.json` does **not** contain `"hosts": ["tcp://..."]`.

**Minimal recommended `/etc/docker/daemon.json`:**

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "no-new-privileges": true,
  "live-restore": true,
  "userland-proxy": false
}
```

### Bind internal service ports to localhost

In production Docker Compose overrides, bind all non-public ports to `127.0.0.1` to prevent Docker's iptables rules from bypassing UFW:

```yaml
# ✅ Correct — only reachable from localhost or WireGuard tunnel
prometheus:
  ports:
    - "127.0.0.1:9090:9090"

grafana:
  ports:
    - "127.0.0.1:3000:3000"

# ❌ Wrong — bypasses UFW and exposes to all interfaces
# prometheus:
#   ports:
#     - "9090:9090"
```

### Use Docker secrets or environment files for sensitive values

- Store secrets in `.env` (excluded from git via `.gitignore`)
- Never `COPY .env` in a `Dockerfile`
- Consider using Docker Swarm secrets or HashiCorp Vault for production-grade secret injection

### Limit container capabilities

Add `security_opt` and `read_only` where possible:

```yaml
services:
  backend:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

### Socket access for ops-heal

The `ops-heal` container mounts `/var/run/docker.sock`. Restrict this to read-only where sufficient, and audit that container for command injection risks:

```yaml
ops-heal:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
```

---

## 6. Security Update Policy

### Automated unattended upgrades (OS packages)

```bash
sudo apt install -y unattended-upgrades apt-listchanges

sudo tee /etc/apt/apt.conf.d/20-swarmenterprise-autoupgrade <<'EOF'
// Automatically apply security updates only
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";  // reboot manually after kernel patches
Unattended-Upgrade::Mail "ops@realms2riches.com";
EOF

sudo systemctl enable --now unattended-upgrades
```

### Docker image update cadence

| Component | Update frequency | Method |
|-----------|-----------------|--------|
| OS base images (`ubuntu:22.04`) | Weekly | Dependabot or Renovate |
| Backend application image | Every deploy (CI/CD) | GitHub Actions |
| `caddy:2-alpine` | Monthly or on CVE | Dependabot |
| `postgres:16-alpine` | Monthly | Dependabot |
| `redis:7-alpine` | Monthly | Dependabot |
| `prom/prometheus`, `grafana/grafana` | Monthly | Dependabot |

Enable Dependabot for Docker images in `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "docker"
    directory: "/deploy/docker"
    schedule:
      interval: "weekly"
```

### Python dependency auditing

The `scripts/pip_audit_gate.py` script audits Python dependencies against the OSV vulnerability database. Run it in CI:

```bash
python scripts/pip_audit_gate.py
```

### Manual security checklist (monthly)

Run the security audit script to validate the current state of the production server:

```bash
sudo bash scripts/security_audit.sh
```

All checks should report `PASS`. Investigate and remediate any `FAIL` before the end of the sprint.

Review and rotate the following secrets every 90 days:

- `JWT_SECRET_KEY`
- `GRAFANA_PASSWORD`
- `DB_PASSWORD` / `POSTGRES_PASSWORD`
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`
- SSH deploy keypairs (revoke and replace any that may have been exposed)

### Incident response

1. **Isolate:** `sudo ufw deny incoming` to cut off all traffic, or `sudo docker compose down` to stop all services.
2. **Investigate:** Review `journalctl`, Docker logs (`docker logs <container>`), and Caddy access logs in `/var/log/caddy/`.
3. **Remediate:** Patch the vulnerability, rotate affected secrets, redeploy.
4. **Post-mortem:** Document root cause and timeline in `docs/post-mortems/`.
