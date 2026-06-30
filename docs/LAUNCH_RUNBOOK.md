# SwarmEnterprise v2 — Production Launch Runbook

**Estimated Duration:** 30–45 minutes  
**Prerequisites:** Complete [Launch Checklist](./LAUNCH_CHECKLIST.md)  
**Owner:** Deployment Team  
**Emergency Contact:** robertdemottojr50@gmail.com

---

## Table of Contents

1. [Pre-Flight (5 min)](#1-pre-flight-checks)
2. [Deploy to Production (20 min)](#2-deploy-to-production)
3. [Smoke Tests & Verification (10 min)](#3-smoke-tests--verification)
4. [Post-Deploy Monitoring (Ongoing)](#4-post-deploy-monitoring)
5. [Rollback Procedure](#5-rollback-procedure)

---

## 1. Pre-Flight Checks

### 1.1 Team Communication

```bash
# Post to #launch-incident channel (Slack/Teams)
🚀 **LAUNCH IN PROGRESS** — SwarmEnterprise v2 to Production
⏱️ Est. duration: 45 min
👥 Monitoring: @devops-team
🆘 Issues: ping @robertdemottojr50@gmail.com
```

### 1.2 Environment & Connectivity

```bash
# SSH to production VM
ssh -i ~/.ssh/deploy_prod deploy@<PRODUCTION_VM_IP>

# Verify we're in the right directory
pwd  # should output: /opt/swarmenterprise

# Verify current commit
git log --oneline -1
```

### 1.3 Backup Current State

```bash
# Backup database (if migration contains schema changes)
docker compose exec postgres pg_dump \
  -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  > /tmp/backup-prod-$(date +%Y%m%d-%H%M%S).sql

# Copy to safe location
scp /tmp/backup-prod-*.sql deploy@<BACKUP_SERVER>:/backups/

# Tag current production image
docker tag ghcr.io/rwv-techsolutions/swarmenterprise:latest \
           ghcr.io/rwv-techsolutions/swarmenterprise:prod-pre-launch-$(date +%Y%m%d)
```

### 1.4 Validate Environment

```bash
# Check all required environment variables
make env-check

# Expected output:
# ✓ JWT_SECRET_KEY is set
# ✓ SECRET_KEY is set
# ✓ POSTGRES_PASSWORD is set
# ✓ STRIPE_API_KEY is set (live key)
# ... all green
```

### 1.5 Health of Current System

```bash
# Check current services status
docker compose ps

# Expected: All services running or not yet started (acceptable)

# If services are running, check health
docker compose exec backend curl http://localhost:8000/health

# Expected output:
# {"status": "ONLINE", "version": "2.0.0", "checks": {"db": "ok", "redis": "ok", "ollama": "ok"}}
```

---

## 2. Deploy to Production

### 2.1 Fetch Latest Code

```bash
git fetch origin
git checkout main  # or specific tag
git pull origin main
```

### 2.2 Build Docker Image (on VM or via CI/CD)

**Option A: Build on VM (slower, ~3–5 min)**

```bash
make build
# or
docker build -f backend/Dockerfile \
  -t ghcr.io/rwv-techsolutions/swarmenterprise:latest \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) .

# Verify build succeeded
docker images | grep swarmenterprise
```

**Option B: Pull pre-built image from registry (faster, recommended)**

```bash
# Assumes GitHub Actions / CI already built and pushed image
docker pull ghcr.io/rwv-techsolutions/swarmenterprise:latest
```

### 2.3 Stop Current Services Gracefully

```bash
# Stop without destroying volumes (persistent data remains)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres --profile proxy --profile workers down

# Verify all containers stopped
docker compose ps

# Expected output: no running containers
```

### 2.4 Run Database Migrations

```bash
# Start postgres and redis for migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres up -d postgres redis

# Wait for postgres to be ready
sleep 5
docker compose exec postgres pg_isready -U ${POSTGRES_USER}

# Expected output: "accepting connections"

# Run migrations
make migrate

# Verify migration succeeded
docker compose exec postgres psql -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  -c "SELECT version FROM alembic_version;"

# Expected output: (one row with migration version)
```

### 2.5 Start Full Production Stack

```bash
# Start all services with production overlay
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres --profile proxy --profile workers up -d --pull always --remove-orphans

# Verify all containers are starting
docker compose ps

# Expected output:
# NAME                 STATUS                           PORTS
# swarmOS-backend      Up 2 seconds (health: starting)  0.0.0.0:8000->8000/tcp
# swarmOS-worker       Up 2 seconds
# swarmOS-beat         Up 2 seconds
# swarmOS-redis        Up 2 seconds (healthy)
# swarmOS-postgres     Up 2 seconds (healthy)
# swarmOS-caddy        Up 2 seconds (healthy)
# swarmOS-flower       Up 2 seconds
```

### 2.6 Wait for Health Checks

```bash
# Poll health endpoint until all checks pass (max 2 min)
make health

# Or manual polling:
for i in {1..24}; do
  echo "Health check $i/24 ..."
  curl -s http://localhost:8000/health | jq .
  if [ $? -eq 0 ]; then break; fi
  sleep 5
done
```

---

## 3. Smoke Tests & Verification

### 3.1 API Smoke Tests

```bash
# Run automated smoke tests
make smoke

# Expected output:
# ✓ GET /health — 200 OK
# ✓ GET /docs — 200 OK (Swagger UI)
# ✓ GET /metrics — 200 OK (Prometheus)
# ✓ POST /auth/register — 200 OK (create test user)
# ✓ POST /auth/login — 200 OK (test login)
# ... all green
```

### 3.2 Manual Verification via curl

```bash
# Test via HTTPS (public endpoint)
BASE_URL="https://api.realms2riches.com"

# Health
curl -s $BASE_URL/health | jq .

# Swagger docs
curl -s -I $BASE_URL/docs | head -5  # should return 200

# Metrics
curl -s $BASE_URL/metrics | head -10  # should show Prometheus metrics

# Create test user (if registration enabled)
curl -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TempPassword123!"}' \
  | jq .

# Expected response: {"user_id": "uuid", "email": "test@example.com"}
```

### 3.3 Web UI Verification

- [ ] Open https://realms2riches.com in a browser
  - [ ] Page loads without errors (check DevTools console)
  - [ ] HTTPS lock icon is visible
  - [ ] CSS/JS resources load (check Network tab)
- [ ] Navigate to https://api.realms2riches.com/docs
  - [ ] Swagger UI displays
  - [ ] "Try it out" button works for `/health` endpoint

### 3.4 Database Connectivity

```bash
# Verify Postgres is responsive
docker compose exec postgres psql -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  -c "SELECT count(*) as table_count FROM information_schema.tables WHERE table_schema='public';"

# Expected output: should show > 20 tables

# Check for any schema issues
docker compose exec postgres psql -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  -c "\dt"  # list all tables
```

### 3.5 Redis Connectivity

```bash
# Verify Redis is responsive
docker compose exec redis redis-cli ping

# Expected output: PONG

# Check memory usage
docker compose exec redis redis-cli info memory | grep used_memory_human

# Expected output: used_memory_human: ~10M (should be low on first launch)
```

### 3.6 Celery Workers

```bash
# Check if workers are active
docker compose exec backend python -c \
  "from backend.celery_app import app; print('Workers:', len(app.control.inspect().active()))"

# Alternative: inspect via Flower (if accessible)
curl -s http://localhost:5555/flower/api/workers | jq .

# Expected output: shows active workers, queue sizes
```

### 3.7 Certificate & SSL Verification

```bash
# Verify SSL certificate is valid
openssl s_client -connect api.realms2riches.com:443 </dev/null 2>&1 | \
  grep -A 2 "subject="

# Expected output:
# subject=CN = api.realms2riches.com
# issuer=C = US, O = Let's Encrypt ...
# (indicates valid Let's Encrypt cert)
```

---

## 4. Post-Deploy Monitoring

### 4.1 Live Monitoring (First 5 minutes)

```bash
# Tail all container logs
docker compose logs -f

# Watch for errors, exceptions, failed health checks
```

### 4.2 Monitor Key Metrics

| Metric | Threshold | Command |
|--------|-----------|---------|
| Error rate | < 1% | `curl http://localhost:9090/api/prom/query?query=rate(http_requests_total{status=~"5.."}[1m])` |
| Response time (p95) | < 500ms | Grafana dashboard |
| Queue depth | < 100 | `docker compose exec redis redis-cli llen celery` |
| Memory usage | < 80% | `docker stats` |
| Disk space | > 10GB free | `df -h /` |

### 4.3 Verify External Integrations

- [ ] **Email**: Send a test email from the admin panel, verify it arrives
- [ ] **Stripe**: Process a test charge (use Stripe test card if `STRIPE_TEST_MODE=TRUE`), verify webhook received
- [ ] **Ollama/LLM**: Trigger a task that uses LLM, verify response
- [ ] **Analytics** (if enabled): Check Umami dashboard for tracking

### 4.4 Check Error Tracking

```bash
# If Sentry is configured
# Open https://sentry.io → select project → look for new errors
# Expected: 0 new errors in first 5 minutes

# Or check logs for stack traces
docker compose logs backend | grep -i "error\|exception\|traceback"
```

### 4.5 Announce to Team

```bash
# Post to #launch-incident (or equivalent)
✅ **LAUNCH SUCCESSFUL** — SwarmEnterprise v2 is LIVE
📊 Status: All checks green
🔗 URLs:
  - API: https://api.realms2riches.com
  - Docs: https://api.realms2riches.com/docs
  - Web: https://realms2riches.com
  - Metrics: https://api.realms2riches.com/metrics

🎉 Ready for production traffic!
```

---

## 5. Rollback Procedure

**Use ONLY if critical issues are discovered post-deploy.**

### 5.1 Immediate Stop

```bash
# Stop all services immediately (preserve data)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres --profile proxy --profile workers down

# Wait for graceful shutdown (max 30s)
sleep 5
```

### 5.2 Revert to Previous Image

```bash
# Pull the pre-launch image
docker pull ghcr.io/rwv-techsolutions/swarmenterprise:prod-pre-launch-YYYYMMDD

# Start with previous image
export BACKEND_IMAGE="ghcr.io/rwv-techsolutions/swarmenterprise:prod-pre-launch-YYYYMMDD"
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres --profile proxy --profile workers up -d --pull always
```

### 5.3 Downgrade Database (if needed)

```bash
# If the previous version uses an older schema
alembic downgrade -1

# Verify schema downgrade succeeded
docker compose exec postgres psql -U ${POSTGRES_USER} \
  -d ${POSTGRES_DB} \
  -c "SELECT version FROM alembic_version;"
```

### 5.4 Verify Rollback

```bash
# Run health checks again
make health

# Run smoke tests
make smoke

# Manually verify critical endpoints
curl https://api.realms2riches.com/health
```

### 5.5 Post-Incident

1. **Document the incident**: What failed, why, how it was detected
2. **Root cause analysis**: Schedule meeting to discuss
3. **Prevention**: Add tests, monitoring, or pre-deployment checks
4. **Communication**: Update team on status and timeline for re-launch

---

## Troubleshooting During Launch

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Migration fails** | Error: `alembic: error: (psycopg2.errors.SyntaxError)...` | Check DATABASE_URL is correct; review migration SQL; roll back and retry |
| **Backend won't start** | Container exits immediately | `docker compose logs backend` — check for config errors, missing secrets |
| **Health check timeout** | Waits 2 min for `/health` to return 200 | Check Postgres is running; verify DATABASE_URL; restart backend |
| **HTTPS certificate fails** | Caddy logs show ACME error | Verify DNS A records are pointing to VM; wait for propagation; check firewall allows 80/443 |
| **Redis connection refused** | Error: `ERR invalid password` | Verify REDIS_URL in .env; ensure Redis container is running; check AUTH password if configured |
| **Celery workers not processing** | Queue depth stays high | Check worker logs: `docker compose logs worker`; verify BROKER_URL matches REDIS_URL |
| **Out of disk space** | Error: `write to disk failed` | Run `docker system prune -f`; delete old backups; expand VM disk |
| **Port already in use** | Error: `bind: address already in use` | `docker compose down --remove-orphans` then retry; or change `BACKEND_PORT` in .env |

---

## Success Criteria

All of the following must be true to consider launch successful:

1. ✅ All containers are running and healthy
2. ✅ Health check endpoint returns `{"status": "ONLINE"}`
3. ✅ API responds to requests with < 500ms latency
4. ✅ Smoke tests pass 100% (no failed requests)
5. ✅ No errors or exceptions in logs (first 5 minutes)
6. ✅ SSL certificate is valid (verified via openssl)
7. ✅ Monitoring & alerting are active
8. ✅ Database backups completed successfully
9. ✅ Team is notified and aware of production status

If ANY of the above fail, follow the [Rollback Procedure](#5-rollback-procedure).

---

**Contact:** robertdemottojr50@gmail.com  
**Last Updated:** 2026-06-29  
**Version:** 1.0
