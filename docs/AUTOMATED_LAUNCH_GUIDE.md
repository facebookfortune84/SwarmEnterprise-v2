# SwarmEnterprise v2 — Automated Launch Guide

**Single source of truth for launching, verifying, and maintaining production.**  
RWV Techsolutions LLC · robertdemottojr50@gmail.com

---

## TL;DR — One Command Launch

```bash
# First time only — copy and fill your secrets
cp .env.example .env
python scripts/generate_secrets.py   # generates JWT_SECRET_KEY, SECRET_KEY, etc.
# then fill STRIPE_*, SMTP_*, POSTGRES_PASSWORD, PRIMARY_DOMAIN in .env

# Full automated launch (pre-check → start → test → verify)
make full-launch
```

That's it. `make full-launch` runs every step automatically.

---

## What Each Automation Does

| Command | What it does |
|---------|-------------|
| `make full-launch` | pre-launch + migrate + seed + start + smoke + verify live |
| `make pre-launch` | checks env vars, secrets strength, Docker, DB, Redis, TLS, Stripe |
| `make launch` | migrate + seed + start services + smoke tests |
| `make verify-live` | tests live API + auth flow + **company builder** end-to-end |
| `make smoke` | fast API smoke tests (health, auth, companies, Stripe routes) |
| `make health` | quick health check of all running services |
| `make rollback-deploy PREV_TAG=sha-abc1234` | re-deploy a previous image tag |
| `make post-launch-verify` | alias for `verify-live` |
| `make notify-deploy` | send deploy notification to Slack / webhook |
| `make stop` | graceful shutdown of all services |

---

## Pre-Launch Checklist (Automated)

Run `make pre-launch` — it validates all of the following automatically:

- ✅ All required environment variables set (no placeholders)
- ✅ JWT_SECRET_KEY and SECRET_KEY ≥ 32 characters
- ✅ ADMIN_PASSWORD not a common/weak value
- ✅ Docker daemon running
- ✅ Docker Compose files present and valid syntax
- ✅ Database reachable (if DATABASE_URL set)
- ✅ Redis reachable
- ✅ Alembic migrations up to date (no pending changes)
- ✅ TLS / PRIMARY_DOMAIN / ACME_EMAIL configured (production only)
- ✅ Stripe key mode matches environment (live key in production)
- ✅ SMTP configured (warns in production if missing)
- ✅ .env not tracked in git
- ✅ .env listed in .gitignore
- ✅ Backup scripts present
- ✅ Ollama accessible (info-level if missing)
- ✅ Admin seed credentials configured

Report saved to: `pre_launch_report.json`

---

## Post-Launch Verification (Automated)

Run `make verify-live` — it tests:

1. **Infrastructure** — `/health` (status=ONLINE, db+redis healthy), `/metrics`, `/docs`
2. **Auth Flow** — register → login → verify token → `/api/users/me`
3. **Company Builder** — POST `/api/companies/` → GET list → GET by ID → verify data
4. **Billing Routes** — Stripe router is mounted and responding
5. **Security Guards** — unauthenticated requests return 401/403
6. **TLS / HTTPS** — valid certificate (HTTPS URLs only)
7. **Performance** — avg response time < 1000ms

Cleanup runs automatically after tests (test user + test company deleted).

Report saved to: `verify_live_report.json` (use `--json path`)

---

## CI/CD Pipeline (Fully Automated)

Every push to `main` triggers:

```
preflight → build-and-push → deploy-staging → smoke-staging
    → deploy-production (manual approval gate) → verify-production
    → notify-success (or notify-failure + auto-rollback)
```

### Pipeline Stages

| Stage | Name | What it does |
|-------|------|-------------|
| 0 | **Pre-flight** | Verifies all required GitHub secrets are configured |
| 1 | **Build + Push** | Multi-arch Docker build, pushed to GHCR |
| 2 | **Deploy Staging** | SSH deploy → pull image → migrate → restart |
| 3 | **Smoke Staging** | Wait for health → smoke_test.sh → Python assertions |
| 4 | **Deploy Production** | Manual approval gate → SSH deploy → auto-health-check → in-deploy rollback |
| 5 | **Verify Production** | Full live verifier (company builder) + artifact report |
| 6 | **Notify** | Slack/webhook notification on success or failure |
| 7 | **Auto-Rollback** | If verify fails, automatically redeploys previous image |

### Required GitHub Secrets

Configure at: **Settings → Secrets and variables → Actions**

| Secret | Description |
|--------|-------------|
| `DOCKER_REGISTRY_USER` | GitHub username |
| `DOCKER_REGISTRY_PASSWORD` | GitHub PAT with `write:packages` |
| `SSH_DEPLOY_HOST` | Production VM IP or hostname |
| `SSH_DEPLOY_USER` | SSH user on production VM |
| `SSH_DEPLOY_PRIVATE_KEY` | Base64-encoded PEM private key |
| `JWT_SECRET_KEY` | 64-char hex (from `python scripts/generate_secrets.py`) |
| `SECRET_KEY` | 64-char hex |
| `ENCRYPTION_KEY` | 32-byte URL-safe key |
| `POSTGRES_PASSWORD` | Strong Postgres password |
| `PRIMARY_DOMAIN` | Production domain (e.g. `realms2riches.com`) |
| `SLACK_WEBHOOK_URL` | *(optional)* Slack incoming webhook URL |
| `DEPLOY_WEBHOOK` | *(optional)* Generic HTTP webhook for notifications |

### Production Approval Gate

Production deployments require **manual approval** via GitHub Environments:

1. Go to: **Settings → Environments → production**
2. Enable **Required reviewers** and add your GitHub username
3. On each deploy, you'll receive an email prompt to approve

---

## Local Development Launch

```bash
# Start dev stack (hot reload, no Caddy proxy)
make dev

# Or start full stack with Caddy
make docker-up-prod

# Tail logs
make logs

# Open shell in backend container
make shell-backend
```

---

## Staging Deployment

```bash
# Manual staging deploy (if not using GitHub Actions)
DEPLOY_PROFILE=staging ./start.sh

# Or:
make start   # uses docker-compose.yml + docker-compose.prod.yml
```

---

## Production Deployment

### Automated (Recommended)

Push to `main` on GitHub → CI/CD pipeline runs → approve production gate → done.

### Manual (Emergency / First Deploy)

```bash
# On production VM:
cd /srv/swarmenterprise
git pull origin main

# Set environment
cp .env.example .env   # first time only
# Edit .env with production values

# Full launch
DEPLOY_PROFILE=production ./start.sh

# Verify
make verify-live

# Or verify against a specific URL
python scripts/verify_live.py --url https://realms2riches.com
```

---

## Rollback

### Automated Rollback (CI/CD)

The pipeline automatically rolls back if `verify-production` fails.

### Manual Rollback

```bash
# Roll back to a previous image tag
make rollback-deploy PREV_TAG=sha-abc1234

# Or on the production server:
cd /srv/swarmenterprise
BACKEND_IMAGE=ghcr.io/your-org/swarmenterprise-backend:sha-abc1234 \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres --profile proxy --profile workers \
  up -d --remove-orphans
make health
```

### Database Rollback

```bash
# Roll back one migration
make rollback

# Roll back to a specific migration
python scripts/run_alembic.py downgrade <revision_id>
```

---

## Monitoring

```bash
# Start Prometheus + Grafana
make monitoring-up

# Access:
#   Grafana:    http://localhost:3000
#   Prometheus: http://localhost:9090

# Tail all logs
make logs

# Health check (JSON output)
curl http://localhost:8000/health | python -m json.tool
```

### Key Metrics to Watch (First 24h)

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| Error rate | > 1% | Check logs, identify root cause |
| P95 latency | > 500ms | Check DB/Redis |
| Queue depth | > 500 tasks | Scale Celery workers |
| Memory | > 80% | Increase RAM or optimize |
| Disk | < 10% free | Clean logs or expand |
| SSL expiry | < 30 days | Verify auto-renewal (Caddy handles this) |

---

## Backup

```bash
# Backup Postgres
bash scripts/backup_postgres.sh

# Backup configuration files
bash scripts/backup_config.sh

# Restore Postgres
bash scripts/restore_postgres.sh /path/to/backup.sql
```

Backups stored in: `./backups/`

---

## Security Checklist (Pre-Public Launch)

- [ ] `ENV=production` in production `.env`
- [ ] `STRIPE_TEST_MODE=FALSE` in production `.env`
- [ ] `DRY_RUN_MODE=false` in production `.env`
- [ ] `OUTREACH_DRY_RUN=false` in production `.env`
- [ ] All secrets ≥ 32 characters (use `python scripts/generate_secrets.py`)
- [ ] `.env` has permissions `600`: `chmod 600 .env`
- [ ] `.env` is in `.gitignore` and NOT tracked by git
- [ ] Firewall allows only ports 80, 443 (block 8000, 5432, 6379 from internet)
- [ ] SSH key-only authentication on production VM
- [ ] Stripe live keys are set (not test keys)
- [ ] `ADMIN_PASSWORD` is unique and stored in your password manager
- [ ] Run `make pre-launch` — zero CRITICAL failures

---

## Notifications Setup

Set in `.env` or GitHub Secrets:

```bash
# Slack incoming webhook
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../...

# Generic HTTP webhook (POST with JSON event payload)
DEPLOY_WEBHOOK=https://your-monitoring.example.com/hooks/deploy
```

Test with:
```bash
make notify-deploy
```

---

## Troubleshooting

### Services not starting

```bash
docker compose ps          # check container status
docker compose logs -f     # tail all logs
make health                # structured health check
```

### Migration fails

```bash
# Check database connection
python scripts/validate_env.py

# Run manually with verbose output
python -m alembic upgrade head --sql   # dry run (SQL only)
python -m alembic upgrade head         # apply

# Check migration history
python -m alembic history
```

### Health check times out

```bash
# Check what's happening inside the container
docker exec swarmOS-backend curl -v http://localhost:8000/health

# Check startup logs
docker logs swarmOS-backend --tail 100
```

### Smoke tests fail

```bash
# Run with verbose output
python scripts/smoke_api.py --base-url http://localhost:8000 --verbose

# Or the bash version
bash scripts/smoke_test.sh http://localhost:8000 --verbose
```

### Company builder not working

```bash
# Run the full live verifier
python scripts/verify_live.py --url http://localhost:8000 --verbose
```

---

## File Map

| File | Purpose |
|------|---------|
| `start.sh` | Main launch script (all environments) |
| `stop.sh` | Graceful shutdown |
| `Makefile` | All automation targets |
| `scripts/pre_launch.py` | Pre-launch checker (15+ checks) |
| `scripts/verify_live.py` | Live environment + company builder verifier |
| `scripts/smoke_api.py` | Python API smoke tests |
| `scripts/smoke_test.sh` | Bash smoke tests |
| `scripts/notify.py` | Deploy notifications (Slack, webhook) |
| `scripts/generate_secrets.py` | Generate cryptographic secrets |
| `scripts/validate_env.py` | Environment variable validator |
| `scripts/wait_healthy.py` | Poll /health until ready |
| `scripts/seed.py` | Seed initial data (idempotent) |
| `scripts/backup_postgres.sh` | Postgres backup |
| `scripts/backup_config.sh` | Configuration backup |
| `.github/workflows/deploy.yml` | CD pipeline (build → stage → prod → verify → notify → rollback) |
| `.github/workflows/ci.yml` | CI pipeline (lint → test → build) |
| `.github/workflows/security-scan.yml` | Trivy + OWASP dependency scan |
| `.github/workflows/performance.yml` | Locust load test gate |
| `.github/workflows/release.yml` | Semantic versioning + CHANGELOG |
| `docker-compose.yml` | Base stack (dev) |
| `docker-compose.prod.yml` | Production overlay (resource limits, health checks) |
| `deploy/Caddyfile` | Caddy reverse proxy config (HTTPS + security headers) |
| `monitoring/prometheus.yml` | Prometheus scrape config |
| `monitoring/grafana/` | Grafana dashboards + provisioning |

---

*SwarmEnterprise v2 — RWV Techsolutions LLC*  
*Contact: robertdemottojr50@gmail.com*
