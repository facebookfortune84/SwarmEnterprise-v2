# Deployment Guide — SwarmEnterprise v2

> **Company:** RWV Techsolutions LLC  
> **Contact:** robertdemottojr50@gmail.com  
> **Product:** SwarmEnterprise v2 / SwarmOS Sovereign Factory

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (5 steps)](#2-quick-start)
3. [Environment Variable Reference](#3-environment-variable-reference)
4. [Production Deployment](#4-production-deployment)
5. [Scaling](#5-scaling)
6. [Monitoring](#6-monitoring)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Docker | 24.x | [Install Docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2 plugin (or standalone v1.29+) | Bundled with Docker Desktop |
| Python | 3.11+ | For local migrations & scripts |
| Git | 2.x | — |
| curl | any | Used by health-check scripts |

> **Windows users:** Run scripts from Git Bash, WSL2, or PowerShell with Unix tools. The `start.sh` / `stop.sh` scripts require a POSIX-compatible shell.

---

## 2. Quick Start

```bash
# Step 1 — Clone the repository
git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git
cd swarmenterprise-v2

# Step 2 — Create your .env from the template
cp .env.example .env

# Step 3 — Generate secure secret values
python scripts/generate_secrets.py

# Step 4 — Fill in the remaining required values in .env
#   Minimum required: DATABASE_URL (or POSTGRES_*), JWT_SECRET_KEY, SECRET_KEY
$EDITOR .env

# Step 5 — Launch everything with a single command
make launch
```

`make launch` executes in order:
1. Validates all required environment variables (`make env-check`)
2. Runs Alembic database migrations (`make migrate`)
3. Seeds initial data — admin user, roles, categories (`make seed`)
4. Builds Docker images and starts all services (`./start.sh`)
5. Polls the `/health` endpoint until the backend is ready
6. Runs API smoke tests to verify the deployment

After launch, the following URLs are available:

| Service | URL |
|---------|-----|
| API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| Health Check | `http://localhost:8000/health` |
| Prometheus Metrics | `http://localhost:8000/metrics` |
| Flower (workers) | `http://localhost:5555` |

---

## 3. Environment Variable Reference

Copy `.env.example` to `.env` and fill in the values. Run `python scripts/generate_secrets.py` to generate cryptographic secrets. Never commit `.env`.

### 3.1 Domains & Deploy Profile

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PRIMARY_DOMAIN` | Optional | `realms2riches.com` | Primary public domain |
| `CORP_DOMAIN` | Optional | — | Corporate portal domain |
| `API_DOMAIN` | Optional | — | API subdomain |
| `DEPLOY_PROFILE` | Optional | `local` | `local` / `staging` / `production` |
| `ACME_EMAIL` | Optional* | — | Let's Encrypt registration email (*required for HTTPS) |
| `BACKEND_IMAGE` | Optional | — | Docker image tag for CI/CD deploys |

### 3.2 Database (PostgreSQL)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Required** (or POSTGRES_*) | — | Full DSN: `postgresql://user:pass@host:5432/db` |
| `POSTGRES_HOST` | Required if no DATABASE_URL | `postgres` | Postgres hostname |
| `POSTGRES_DB` | Required if no DATABASE_URL | `swarm` | Database name |
| `POSTGRES_USER` | Required if no DATABASE_URL | `swarm` | Database user |
| `POSTGRES_PASSWORD` | **Required** | — | Database password |
| `POSTGRES_PORT` | Optional | `5432` | Database port |

### 3.3 Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Optional | `redis://redis:6379/0` | Redis connection URL; add `:password@` for auth |

### 3.4 Authentication & Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | **Required** | — | 64-char hex — HMAC key for JWT signing |
| `SECRET_KEY` | **Required** | — | 64-char hex — session & cookie signing key |
| `ENCRYPTION_KEY` | Optional | — | 32-byte URL-safe base64 — PII encryption key |

### 3.5 Admin Seed

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADMIN_EMAIL` | Optional | `admin@swarmenterprise.local` | Admin user email created at first seed |
| `ADMIN_PASSWORD` | Optional | *(insecure default)* | Admin user password — **always override in production** |

### 3.6 LLM Providers

| Variable | Required | Description |
|----------|----------|-------------|
| `OLLAMA_URL` | Optional | Local Ollama endpoint, e.g. `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | Optional | Model to use, e.g. `llama3.2:3b` |
| `GROQ_API_KEY` | Optional | Groq cloud inference key |
| `GOOGLE_API_KEY` | Optional | Google Generative AI key |
| `ANTHROPIC_API_KEY` | Optional | Anthropic Claude key |
| `OPENAI_API_KEY` | Optional | OpenAI key |

### 3.7 Email (SMTP)

| Variable | Required | Description |
|----------|----------|-------------|
| `SMTP_SERVER` | Optional* | SMTP hostname (*required for email features) |
| `SMTP_PORT` | Optional | Default `587` (STARTTLS) |
| `SMTP_USER` | Optional* | SMTP login username |
| `SMTP_PASS` | Optional* | SMTP password or app password |
| `CONTACT_EMAIL` | Optional | Public contact address in outbound mail |

### 3.8 Payments (Stripe)

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIPE_API_KEY` | Optional* | Secret key `sk_live_…` or `sk_test_…` (*required for payments) |
| `STRIPE_WEBHOOK_SECRET` | Optional* | Webhook signing secret `whsec_…` |
| `STRIPE_PUBLISHABLE_KEY` | Optional | Publishable key for frontend |
| `STRIPE_TEST_MODE` | Optional | `TRUE` to use test keys |

### 3.9 Telemetry & Monitoring

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | Optional | — | Sentry error tracking DSN |
| `OTEL_OTLP_ENDPOINT` | Optional | — | OpenTelemetry collector endpoint |
| `OTEL_SDK_DISABLED` | Optional | `true` | Set `false` to enable OTEL tracing |
| `LOG_LEVEL` | Optional | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `ENV` | Optional | `development` | `development` / `staging` / `production` |

### 3.10 CORS & URLs

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | Optional | localhost + realms2riches.com | Comma-separated allowed origins |
| `FRONTEND_URL` | Optional | — | Frontend base URL |
| `BACKEND_URL` | Optional | — | Backend base URL |
| `BACKEND_PORT` | Optional | `8000` | Port the backend listens on |

### 3.11 Runtime Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OUTREACH_ENABLED` | Optional | `true` | Enable autonomous outreach agent |
| `OUTREACH_DRY_RUN` | Optional | `true` | `true` = no live sends |
| `DRY_RUN_MODE` | Optional | `true` | Master dry-run flag (no real side effects) |
| `ANALYTICS_ENABLED` | Optional | `false` | Enable usage analytics |
| `CIRCUIT_BREAKER_THRESHOLD` | Optional | `5` | Failure count before circuit opens |
| `TASK_QUEUE_MAX_SIZE` | Optional | `1000` | Max queued tasks |
| `OPS_HEAL_INTERVAL_SEC` | Optional | `300` | Self-healing check interval (seconds) |

### 3.12 Flower (Celery UI)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLOWER_USER` | Optional | `admin` | Flower basic-auth username |
| `FLOWER_PASSWORD` | Optional | `changeme` | Flower basic-auth password — **change in production** |

---

## 4. Production Deployment

### 4.1 Cloud VM Setup

**Recommended specs (entry level):**
- 4 vCPU / 8 GB RAM / 80 GB SSD (e.g. IONOS VPS L, AWS t3.large, DigitalOcean Droplet 8GB)
- Ubuntu 22.04 LTS

```bash
# On the VM — initial setup
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y docker.io docker-compose-plugin git curl

# Add deploy user to docker group
sudo usermod -aG docker $USER && newgrp docker

# Clone and configure
git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git /opt/swarmenterprise
cd /opt/swarmenterprise
cp .env.example .env
# Edit .env with production values
python3 scripts/generate_secrets.py

# Launch
make launch
```

### 4.2 SSL with Caddy

The `proxy` profile starts Caddy which automatically provisions Let's Encrypt certificates. Ensure:

1. DNS A records for `PRIMARY_DOMAIN`, `API_DOMAIN`, and `CORP_DOMAIN` point to your VM's IP.
2. `ACME_EMAIL` is set in `.env`.
3. Ports 80 and 443 are open in your firewall / security group.

```bash
# Start with proxy profile
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile proxy --profile postgres up -d
```

### 4.3 Cloudflare (Optional)

If routing traffic through Cloudflare:

1. Set SSL/TLS mode to **Full (strict)** in the Cloudflare dashboard.
2. Set `CLOUDFLARE_TUNNEL_TOKEN` in `.env` to use Zero Trust Tunnel (no open inbound ports required).
3. In Cloudflare Zero Trust → Tunnels, add public hostnames mapping to `http://backend:8000`.

### 4.4 Environment Hardening Checklist

- [ ] `DRY_RUN_MODE=false` and `OUTREACH_DRY_RUN=false` after testing
- [ ] `STRIPE_TEST_MODE=FALSE` with live Stripe keys
- [ ] `ENV=production`
- [ ] `ADMIN_PASSWORD` set to a strong, unique password
- [ ] `FLOWER_PASSWORD` changed from default
- [ ] `CORS_ORIGINS` set to your specific domain(s)
- [ ] `ENCRYPTION_KEY` generated and stored securely
- [ ] `SENTRY_DSN` configured for error tracking
- [ ] Firewall blocks direct access to ports 5432 (Postgres), 6379 (Redis), 5555 (Flower)

---

## 5. Scaling

### 5.1 Horizontal Scaling (Multiple Workers)

Celery workers scale independently of the API:

```bash
# Scale to 3 Celery workers
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile workers up -d --scale worker=3
```

### 5.2 Database Scaling

**Read replicas (PostgreSQL):**
1. Provision a replica (e.g. AWS RDS read replica, or `pg_basebackup`).
2. Set `DATABASE_URL` for writes and a separate `DATABASE_READ_URL` (if supported by app code) for reads.

**Connection pooling:**
Add PgBouncer between the app and Postgres for high-concurrency workloads:
```yaml
# Add to docker-compose.prod.yml
pgbouncer:
  image: bitnami/pgbouncer:latest
  environment:
    POSTGRESQL_HOST: postgres
    POSTGRESQL_DATABASE: ${POSTGRES_DB}
    PGBOUNCER_MAX_CLIENT_CONN: 1000
    PGBOUNCER_POOL_MODE: transaction
```

### 5.3 Redis Scaling

For high-volume task queues, replace the single Redis node with Redis Sentinel or Redis Cluster and update `REDIS_URL` accordingly.

---

## 6. Monitoring

### 6.1 Built-in Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service liveness — returns `{"status": "ONLINE"}` |
| `GET /metrics` | Prometheus metrics (request count, latency, status codes) |

### 6.2 Prometheus + Grafana

Start the monitoring stack:

```bash
make monitoring-up
```

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Prometheus | `http://localhost:9090` | none |
| Grafana | `http://localhost:3000` | admin / admin |

Import the SwarmOS dashboard from `deploy/docker/grafana/dashboards/`.

### 6.3 Sentry Error Tracking

Set `SENTRY_DSN` in `.env`. All unhandled exceptions are captured automatically via `sentry-sdk`.

### 6.4 Celery Monitoring (Flower)

Flower is available at `http://localhost:5555` when running with the `workers` profile.  
Protect with `FLOWER_USER` / `FLOWER_PASSWORD` in production.

### 6.5 Alerting

Configure Grafana alert rules or Prometheus Alertmanager to notify `robertdemottojr50@gmail.com` on:
- Backend health check failures (> 2 minutes)
- Error rate > 5% over 5 minutes
- Celery queue depth > 500 tasks
- Postgres connection errors

---

## 7. Troubleshooting

### Backend won't start

```bash
# Check logs
docker compose logs backend

# Validate environment
make env-check

# Verify database is up
docker compose ps postgres
docker compose exec postgres pg_isready -U swarm
```

### Migration fails

```bash
# Check DATABASE_URL is correct
echo $DATABASE_URL

# Run migration manually with verbose output
alembic upgrade head --sql    # dry-run: prints SQL without executing
alembic upgrade head          # apply

# Check current migration state
alembic current
alembic history
```

### Seed fails

```bash
# Check seed state
python scripts/seed.py --check && echo "already seeded" || echo "not seeded"

# Force reseed (safe — all inserts use ON CONFLICT DO NOTHING)
python scripts/seed.py --force
```

### Health check timeout

```bash
# Start.sh polls /health for 60s. To investigate:
curl -v http://localhost:8000/health

# Check if the container is running
docker compose ps

# Check container startup logs
docker compose logs --tail=50 backend
```

### Redis connection refused

```bash
docker compose ps redis
docker compose exec redis redis-cli ping
# Expected output: PONG
```

### Celery tasks not processing

```bash
# Check worker logs
docker compose logs worker

# Inspect queue via Flower: http://localhost:5555

# Or via CLI
docker compose exec worker celery -A backend.celery_app inspect active
```

### SSL certificate issues (Caddy)

```bash
# Check Caddy logs
docker compose logs caddy

# Common causes:
# - DNS not propagated yet (wait up to 24h)
# - Port 80/443 blocked by firewall
# - ACME_EMAIL not set in .env
```

### Out of disk space

```bash
# Remove unused Docker data
docker system prune -f

# Check volume sizes
docker system df

# Remove specific volumes (WARNING: permanent data loss)
docker volume rm swarmenterprise-v2_pg_data   # loses all DB data
```

---

*SwarmEnterprise v2 — RWV Techsolutions LLC*  
*Contact: robertdemottojr50@gmail.com*
