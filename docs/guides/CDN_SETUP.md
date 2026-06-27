# CDN & Rate Limiting Setup Guide

This guide covers Cloudflare CDN configuration for SwarmEnterprise v2 (`realms2riches.com`), including cache rules, firewall hardening, Cloudflare Tunnel, and deployment cache purging.

---

## Table of Contents

1. [DNS Configuration (Orange-Cloud)](#1-dns-configuration-orange-cloud)
2. [Cache Rules for Static Assets](#2-cache-rules-for-static-assets)
3. [Cache-Control via Transform Rules](#3-cache-control-via-transform-rules)
4. [Firewall: Accept Only Cloudflare IPs](#4-firewall-accept-only-cloudflare-ips)
5. [Cloudflare Tunnel (Zero Port Exposure)](#5-cloudflare-tunnel-zero-port-exposure)
6. [Purge Cache on Deployment](#6-purge-cache-on-deployment)
7. [Rate Limiting at the Caddy Layer](#7-rate-limiting-at-the-caddy-layer)

---

## 1. DNS Configuration (Orange-Cloud)

"Orange-clouding" a DNS record proxies all traffic through Cloudflare before it reaches your origin server. This gives you CDN caching, DDoS mitigation, and hides your real server IP.

### Steps

1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com) and select your zone (`realms2riches.com`).
2. Go to **DNS → Records**.
3. For each hostname pointing to your server, ensure the **Proxy status** column shows the orange cloud icon (not grey):

   | Type | Name                 | Content          | Proxy status |
   |------|----------------------|------------------|--------------|
   | A    | `@`                  | `<your-server-IP>` | ✅ Proxied   |
   | A    | `www`                | `<your-server-IP>` | ✅ Proxied   |
   | A    | `api`                | `<your-server-IP>` | ✅ Proxied   |
   | A    | `corp`               | `<your-server-IP>` | ✅ Proxied   |

4. Click the orange/grey cloud icon to toggle proxying on any record that is currently grey.

> **Note:** Wildcard records (`*.realms2riches.tech`) require a Cloudflare Pro plan or above to be proxied.

---

## 2. Cache Rules for Static Assets

Cloudflare's **Cache Rules** (formerly Page Rules → Cache Level) let you instruct Cloudflare to store static assets at the edge so they are served without hitting your origin.

### Create a Cache Rule

1. In the dashboard, go to **Caching → Cache Rules → Create rule**.
2. Name it `Cache static assets`.
3. Set the **When** condition to match static file extensions:

   ```
   (http.request.uri.path matches ".*\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|webp|avif|map)$")
   ```

4. Under **Then**, set:
   - **Cache eligibility**: Cache everything
   - **Edge TTL**: Respect origin, or override to `1 year` (31 536 000 s) for immutable assets
   - **Browser TTL**: Respect origin (Caddy already sends `Cache-Control: public, max-age=31536000, immutable`)

5. Save and deploy.

### Additional rule — bypass cache for API routes

Create a second rule **above** the static rule (rules are evaluated top-to-bottom):

```
(http.request.uri.path matches "^/api/")
```

Set **Cache eligibility** to **Bypass cache** so API responses are never stale.

---

## 3. Cache-Control via Transform Rules

Caddy already emits the correct `Cache-Control` header for static assets (see `deploy/Caddyfile` — the `(static_cache)` snippet). Cloudflare will respect and forward that header to browsers.

If you need to **add or override** `Cache-Control` at the Cloudflare edge (e.g., for an origin that does not set the header):

1. Go to **Rules → Transform Rules → Modify Response Header → Create rule**.
2. Name it `Add Cache-Control for static assets`.
3. **When**: same expression as §2 above.
4. **Then → Set static** header:
   - Header name: `Cache-Control`
   - Value: `public, max-age=31536000, immutable`
5. Save and deploy.

> Because Caddy already sends this header, this Transform Rule is a belt-and-suspenders fallback.

---

## 4. Firewall: Accept Only Cloudflare IPs

When your DNS is orange-clouded, all legitimate traffic arrives from Cloudflare's edge nodes. Blocking direct access to your origin's ports 80/443 from non-Cloudflare IPs prevents attackers who discover your real IP from bypassing the CDN.

### Cloudflare IP Ranges

Current IPv4 and IPv6 ranges are published at:

- **https://www.cloudflare.com/ips-v4**
- **https://www.cloudflare.com/ips-v6**
- Machine-readable JSON: **https://api.cloudflare.com/client/v4/ips**

### iptables / ufw (Linux origin server)

```bash
# Allow SSH first (do NOT lock yourself out)
ufw allow 22/tcp

# Fetch Cloudflare IPv4 ranges and allow them on 80 + 443
curl -s https://www.cloudflare.com/ips-v4 | while read cidr; do
  ufw allow from "$cidr" to any port 80,443 proto tcp
done

# Fetch Cloudflare IPv6 ranges
curl -s https://www.cloudflare.com/ips-v6 | while read cidr; do
  ufw allow from "$cidr" to any port 80,443 proto tcp
done

# Block everything else on 80/443
ufw deny 80/tcp
ufw deny 443/tcp

ufw enable
```

> Re-run this script whenever Cloudflare publishes new IP ranges (subscribe to https://www.cloudflare.com/ips/ for change notifications).

### Docker / host firewall

If your Caddy container binds directly to the host, set `ports` in `docker-compose.yml` to bind only to localhost and rely on the server firewall above:

```yaml
services:
  caddy:
    ports:
      - "127.0.0.1:80:80"    # only reachable via Cloudflare Tunnel or CF IPs
      - "127.0.0.1:443:443"
```

When using **Cloudflare Tunnel** (§5), you can remove the published ports entirely — Caddy only needs to be reachable on its internal Docker network.

---

## 5. Cloudflare Tunnel (Zero Port Exposure)

Cloudflare Tunnel (`cloudflared`) creates an outbound-only encrypted connection from your server to Cloudflare's edge. No inbound ports need to be open, eliminating the attack surface entirely.

### Prerequisites

- A `CLOUDFLARE_TUNNEL_TOKEN` value in your `.env` / `.env.example`. This token is generated by Cloudflare when you create a tunnel and authorises `cloudflared` to authenticate.

### One-time tunnel creation (via dashboard)

1. Go to **Zero Trust → Networks → Tunnels → Create a tunnel**.
2. Choose **Cloudflared**, name it (e.g., `swarm-prod`).
3. Copy the **Tunnel token** — paste it as `CLOUDFLARE_TUNNEL_TOKEN` in `.env`.
4. Under **Public Hostname**, add:

   | Subdomain | Domain                | Service                     |
   |-----------|-----------------------|-----------------------------|
   | (blank)   | `realms2riches.com`   | `http://caddy:80`           |
   | `www`     | `realms2riches.com`   | `http://caddy:80`           |
   | `api`     | `realms2riches.com`   | `http://caddy:80`           |
   | `corp`    | `realms2riches.com`   | `http://caddy:80`           |

   Adjust the service URL to match your Caddy container name and port inside the Docker network.

### docker-compose snippet

Add this service to `deploy/docker-compose.yml` (or `docker-compose.prod.yml`):

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run
    environment:
      TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - swarm_net
```

With this in place, **remove** the `ports:` section from the Caddy service — it no longer needs to bind to the host network.

### TLS with Cloudflare Tunnel

Because the tunnel terminates at Cloudflare's edge (full TLS), and `cloudflared` talks to Caddy over the private Docker network (plain HTTP is fine internally), you can simplify Caddy's TLS config for the tunnel scenario by binding on plain HTTP internally while Cloudflare handles the public certificate. Caddy's ACME config in the global block is still used if you ever fall back to direct-access mode.

---

## 6. Purge Cache on Deployment

After deploying a new version, stale assets cached by Cloudflare must be invalidated. There are two approaches:

### Option A — Purge by tag / prefix (recommended)

Use Cloudflare's **Cache Purge API**. Add this step to your CI/CD pipeline (GitHub Actions, etc.):

```bash
# Required env vars: CF_ZONE_ID, CF_API_TOKEN (Cache Purge permission)
curl -s -X POST \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything": true}'
```

> `purge_everything` is the simplest option for infrequent deploys. For high-traffic sites, prefer purging by URL list or cache tag to avoid a cache-miss spike.

#### Purge specific URLs

```bash
curl -s -X POST \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{
    "files": [
      "https://realms2riches.com/",
      "https://realms2riches.com/index.html"
    ]
  }'
```

### Option B — Content-hashed filenames (zero-purge approach)

The frontend build toolchain (Vite/webpack) already appends a content hash to every JS/CSS bundle filename (e.g., `main.a1b2c3d4.js`). Because Cloudflare caches by URL, a new hash = a new URL = automatically fresh. Only the root `index.html` (which references the new hashed filenames) needs to be purged after each deploy:

```bash
# Purge only index.html after each deploy
curl -s -X POST \
  "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{"files": ["https://realms2riches.com/index.html", "https://realms2riches.com/"]}'
```

This is the preferred approach because it minimises cache churn while ensuring users always get the latest entry point.

### GitHub Actions example

```yaml
- name: Purge Cloudflare cache
  if: success()
  env:
    CF_ZONE_ID: ${{ secrets.CF_ZONE_ID }}
    CF_API_TOKEN: ${{ secrets.CF_API_TOKEN }}
  run: |
    curl -s -X POST \
      "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/purge_cache" \
      -H "Authorization: Bearer ${CF_API_TOKEN}" \
      -H "Content-Type: application/json" \
      --data '{"files": ["https://realms2riches.com/index.html", "https://realms2riches.com/"]}'
```

Add `CF_ZONE_ID` and `CF_API_TOKEN` as repository secrets. The API token needs the **Cache Purge** permission on the target zone only.

---

## 7. Rate Limiting at the Caddy Layer

`deploy/Caddyfile` defines a `@ratelimit` named matcher on all `/api/*` paths and contains the full configuration block for the [`caddy-ratelimit`](https://github.com/mholt/caddy-ratelimit) module, commented out pending module installation.

### Build Caddy with the rate-limit module

```bash
# Install xcaddy (the Caddy custom-build tool)
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest

# Build Caddy with the rate-limit module
xcaddy build \
  --with github.com/mholt/caddy-ratelimit

# Replace the caddy binary in your image
cp caddy /usr/bin/caddy
```

Or add it to a custom Dockerfile:

```dockerfile
FROM caddy:builder AS builder
RUN xcaddy build \
    --with github.com/mholt/caddy-ratelimit

FROM caddy:latest
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

Once the module is present, uncomment the `rate_limit { … }` blocks in `deploy/Caddyfile`.

### Cloudflare Rate Limiting (edge layer)

For an additional layer of protection before traffic reaches your origin:

1. Go to **Security → WAF → Rate limiting rules → Create rule**.
2. Set the expression to match API paths:
   ```
   (http.request.uri.path matches "^/api/")
   ```
3. **Characteristics**: IP address (`ip.src`)
4. **Threshold**: 100 requests per 60 seconds
5. **Action**: Block (or Managed Challenge for softer enforcement)

This enforces rate limiting at the Cloudflare edge, saving origin resources even before `caddy-ratelimit` acts.

---

## Environment Variables Reference

| Variable                   | Description                                              |
|----------------------------|----------------------------------------------------------|
| `CLOUDFLARE_TUNNEL_TOKEN`  | Token for `cloudflared` tunnel authentication            |
| `CF_ZONE_ID`               | Cloudflare Zone ID (found in the dashboard Overview tab) |
| `CF_API_TOKEN`             | API token with Cache Purge permission on the zone        |
| `ACME_EMAIL`               | Email for Let's Encrypt certificate notifications        |

All of these should be present in `.env` (see `.env.example`). Never commit real values to source control.
