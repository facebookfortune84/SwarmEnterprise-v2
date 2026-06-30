# SwarmEnterprise v2 — Production Launch Checklist

**Last Updated:** 2026-06-29  
**Status:** Pre-Launch  
**Owner:** RWV Techsolutions LLC

---

## Pre-Launch (Days 1–3)

### Security & Secrets

- [ ] **JWT_SECRET_KEY** generated via `python scripts/generate_secrets.py`
- [ ] **SECRET_KEY** generated via `python scripts/generate_secrets.py`
- [ ] **ENCRYPTION_KEY** generated via `python scripts/generate_secrets.py`
- [ ] All secrets stored in **1Password / HashiCorp Vault** (never in git)
- [ ] `.env` file has strict permissions: `chmod 600 .env`
- [ ] `.env` is listed in `.gitignore` (verified)
- [ ] **ADMIN_PASSWORD** set to unique, 16+ char password
- [ ] **FLOWER_PASSWORD** changed from default (`changeme`)
- [ ] **SMTP_PASS** and **IMAP_PASS** are app-specific passwords (not account password)
- [ ] **Stripe keys** are LIVE keys (not test keys) if `STRIPE_TEST_MODE=FALSE`
- [ ] All SSH deploy keys are base64-encoded and stored in GitHub Actions secrets
- [ ] Rate limiting configured: `RATE_LIMIT_RPM=120` (adjust based on expected load)

### Infrastructure

- [ ] **Cloud VM provisioned** (e.g. IONOS VPS L: 4vCPU/8GB/80GB SSD, Ubuntu 22.04 LTS)
- [ ] **Docker 24.x** and **Docker Compose v2** installed on VM
- [ ] **DNS A records** created:
  - `PRIMARY_DOMAIN` → VM IP
  - `API_DOMAIN` → VM IP
  - `CORP_DOMAIN` → VM IP
- [ ] **Firewall rules** allow inbound:
  - 80/tcp (HTTP) — for Let's Encrypt ACME challenges
  - 443/tcp (HTTPS) — for production traffic
  - 443/udp (HTTP/3)
- [ ] **Firewall rules** DENY inbound:
  - 5432/tcp (Postgres) — internal only
  - 6379/tcp (Redis) — internal only
  - 5555/tcp (Flower) — internal only
- [ ] **SSH key pair** generated for deploy user (stored in GitHub Actions secrets)
- [ ] **DB backup strategy** documented:
  - [ ] Daily automated snapshots via cloud provider
  - [ ] OR manual `pg_dump` to S3 before each deploy
- [ ] **Disk space** on VM: > 50GB free (for OS, Docker, logs, data)

### Database

- [ ] **PostgreSQL 16** connection tested: `psql -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_HOST -c "SELECT 1"`
- [ ] **DATABASE_URL** is set and valid format: `postgresql+asyncpg://user:pass@host:5432/db`
- [ ] **POSTGRES_PASSWORD** is strong (16+ chars, mixed alphanumeric + special)
- [ ] Initial migrations run: `make migrate`
- [ ] Initial seed data loaded: `make seed`
- [ ] Admin user created with secure password
- [ ] **Connection pool size** tuned:
  - Small: 5 (for dev/test)
  - Medium: 20 (for production small, <1000 rps)
  - Large: 50+ (for high concurrency; add PgBouncer)

### Redis

- [ ] **Redis 7** is running and accessible: `redis-cli ping`
- [ ] **AOF persistence** enabled: `appendonly yes`
- [ ] **Max memory policy** set: `maxmemory-policy allkeys-lru` (or `volatile-lru`)
- [ ] **Max memory** tuned based on RAM: `maxmemory 512mb` for 8GB VM
- [ ] **REDIS_URL** is set: `redis://user:pass@host:6379/0` (add auth if needed)

### LLM & AI

- [ ] **Ollama** running and accessible (local) OR endpoints configured for Groq/Google/Anthropic
- [ ] **OLLAMA_URL** points to correct endpoint: `http://host.docker.internal:11434` (local) or remote
- [ ] **OLLAMA_MODEL** set: `llama3.2:3b` (or your choice)
- [ ] Model downloaded and tested: `curl $OLLAMA_URL/api/tags`
- [ ] **API keys** set for external LLM providers if used:
  - [ ] `GROQ_API_KEY` (Groq)
  - [ ] `GOOGLE_API_KEY` (Google Generative AI)
  - [ ] `ANTHROPIC_API_KEY` (Claude)
  - [ ] `OPENAI_API_KEY` (if using OpenAI)

### Email & Communications

- [ ] **SMTP server** configured and tested:
  - [ ] `SMTP_SERVER` set (e.g. `smtp.sendgrid.net`)
  - [ ] `SMTP_USER` and `SMTP_PASS` are correct app-specific credentials
  - [ ] `SMTP_PORT` is 587 (STARTTLS) or 465 (SSL)
  - [ ] Test send: `python scripts/test_smtp.py`
- [ ] **CONTACT_EMAIL** set to monitored address (e.g. `ops@realms2riches.com`)
- [ ] **SMTP inbound** (IMAP) configured if parsing replies:
  - [ ] `IMAP_SERVER`, `IMAP_USER`, `IMAP_PASS` set

### Payments

- [ ] **Stripe** account created and verified
- [ ] **STRIPE_API_KEY** set to LIVE secret key (`sk_live_…`)
- [ ] **STRIPE_PUBLISHABLE_KEY** set to LIVE publishable key (`pk_live_…`)
- [ ] **STRIPE_WEBHOOK_SECRET** obtained and set (`whsec_…`)
- [ ] **Webhook endpoint** registered in Stripe Dashboard:
  - [ ] URL: `https://api.realms2riches.com/webhooks/stripe`
  - [ ] Events: `charge.succeeded`, `charge.failed`, `customer.subscription.updated`, etc.
- [ ] **Test transaction** processed successfully
- [ ] **Stripe TEST_MODE** set to `FALSE` in production `.env`

### Monitoring & Observability

- [ ] **Sentry** account created if error tracking needed
- [ ] **SENTRY_DSN** set in `.env`
- [ ] **Log level** set to `INFO` in production: `LOG_LEVEL=INFO`
- [ ] **ENV** set to `production`: `ENV=production`
- [ ] **Prometheus** endpoints accessible: `http://localhost:9000/metrics`
- [ ] **Grafana** dashboards imported (optional but recommended)
- [ ] **Alert rules** configured:
  - [ ] Alert on backend health check failures
  - [ ] Alert on error rate > 5% over 5 minutes
  - [ ] Alert on Celery queue depth > 500
  - [ ] Alert on Postgres connection errors
- [ ] **Log aggregation** set up (optional: ELK, Splunk, CloudWatch)

### Deployment & CI/CD

- [ ] **GitHub Actions workflows** enabled and configured:
  - [ ] `.github/workflows/ci.yml` runs tests on push
  - [ ] `.github/workflows/deploy.yml` deploys on merge to `main`
  - [ ] Secrets stored in GitHub repo settings (PROD_SSH_KEY, PROD_SSH_HOST, PROD_SSH_USER)
- [ ] **Docker image** builds successfully: `make build`
- [ ] **Docker image** pushed to registry:
  - [ ] `GHCR_USERNAME` and `GHCR_PASSWORD` configured
  - [ ] Image tagged and pushed: `docker push ghcr.io/rwv-techsolutions/swarmenterprise:latest`
- [ ] **Docker Compose** files verified:
  - [ ] `docker-compose.yml` (base)
  - [ ] `docker-compose.prod.yml` (production hardening)
  - [ ] All volumes use named volumes (no bind mounts for persistent data)
  - [ ] Resource limits configured (memory, CPU)
- [ ] **Deployment script** tested on staging VM

---

## Launch Day (Day 4)

### Pre-Flight (1 hour before)

- [ ] **Backup production DB** (if existing): `pg_dump > backup-$(date +%s).sql`
- [ ] **Team notification**: Slack / email that deployment is starting
- [ ] **Incident channel** open: #launch-incident (for real-time updates)
- [ ] **Rollback plan** documented and tested (revert to previous image, downgrade migration)

### Deploy & Smoke Test (15–30 min)

1. **SSH to VM:**
   ```bash
   ssh -i deploy_key deploy@vm.ip.address
   cd /opt/swarmenterprise
   ```

2. **Pull latest code:**
   ```bash
   git fetch origin && git checkout main && git pull
   ```

3. **Update .env with production values:**
   ```bash
   cp .env.example .env
   # Fill in all production secrets (use SSH copy-paste or `scp`)
   ```

4. **Validate environment:**
   ```bash
   make env-check
   ```

5. **Run migrations:**
   ```bash
   make migrate
   ```

6. **Seed initial data (if new deployment):**
   ```bash
   make seed
   ```

7. **Build and start services:**
   ```bash
   make docker-build
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     --profile postgres --profile proxy --profile workers up -d --pull always
   ```

8. **Wait for health checks (2–3 min):**
   ```bash
   make health
   ```

9. **Run smoke tests:**
   ```bash
   make smoke
   ```

10. **Manual verification:**
    - [ ] API responsive: `curl https://api.realms2riches.com/health`
    - [ ] Health endpoint: `curl https://api.realms2riches.com/health`
    - [ ] Frontend loads: `https://realms2riches.com`
    - [ ] Swagger docs accessible: `https://api.realms2riches.com/docs`
    - [ ] Metrics exposed: `curl https://api.realms2riches.com/metrics`
    - [ ] Flower accessible (internal): `http://<vm-ip>:5555` (basic auth)

### Post-Deploy (1 hour after)

- [ ] **Monitor logs**: `docker compose logs -f backend`
- [ ] **Check error rate**: Sentry / logs for any exceptions
- [ ] **Verify Celery workers**: `curl http://localhost:5555/flower/api/workers` (if accessible)
- [ ] **Load test (light)**: Send 10 requests/sec for 2 minutes, verify no failures
- [ ] **Announce to team**: Deployment successful, system is live
- [ ] **Post-launch communication**: Email to stakeholders with URLs and status

---

## Post-Launch (Days 5+)

### Week 1

- [ ] **Monitor error rates**: < 1% acceptable, target < 0.5%
- [ ] **Monitor latency**: p95 < 500ms, p99 < 1000ms
- [ ] **Monitor queue depth**: Celery queue size < 100 at peak
- [ ] **Database backups**: Verify first automated backup completed
- [ ] **SSL certificate**: Verify auto-renewal is scheduled for 30 days before expiry
- [ ] **User onboarding**: First users can sign up and access dashboard
- [ ] **Payments**: Test charge goes through (can be refunded)

### Month 1

- [ ] **Scale workers** if queue depth trending > 200
- [ ] **Tune database** if connection pool exhaustion observed
- [ ] **Security audit**: Review access logs for anomalies
- [ ] **Feature feedback**: Gather user feedback, iterate on top issues
- [ ] **Performance tuning**: Identify slow endpoints, optimize queries

### Ongoing

- [ ] **Daily backup verification**: Confirm backups are occurring
- [ ] **Monthly security updates**: Patch Docker base images, Python dependencies
- [ ] **Quarterly capacity planning**: Review growth trends, provision ahead
- [ ] **Incident post-mortems**: Document any downtime, root-cause analysis, prevention

---

## Rollback Plan

**If launch fails or critical issues arise:**

1. **Revert to previous image:**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     --profile postgres --profile proxy --profile workers down
   
   docker image rm ghcr.io/rwv-techsolutions/swarmenterprise:latest
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     --profile postgres --profile proxy --profile workers up -d --pull always
   ```

2. **Downgrade database migration (if schema changed):**
   ```bash
   alembic downgrade -1
   ```

3. **Restore from backup (if data corruption):**
   ```bash
   docker compose exec postgres psql -U swarm < backup-XXXXXXXXX.sql
   ```

4. **Notify team** and run post-incident review.

---

**Next Step:** Follow the [Launch Runbook](./LAUNCH_RUNBOOK.md) for the actual deployment procedure.

