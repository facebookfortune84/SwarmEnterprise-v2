# Deployment Guide — SwarmEnterprise v2

This document covers local development setup, Docker-based deployment,
environment variable reference, database migrations, Celery workers, smoke
testing, and a production readiness checklist.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Environment Variable Reference](#environment-variable-reference)
4. [Docker Compose Deployment](#docker-compose-deployment)
5. [Database Migrations](#database-migrations)
6. [Celery Workers and Beat Scheduler](#celery-workers-and-beat-scheduler)
7. [Smoke Tests](#smoke-tests)
8. [Production Readiness Checklist](#production-readiness-checklist)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|----------------|-------|
| Python | 3.11 | `python --version` |
| Docker | 24.x | `docker --version` |
| Docker Compose | 2.x (plugin) | `docker compose version` |
| PostgreSQL | 16 (via Docker) | Only needed for production |
| Redis | 7 (via Docker) | Used for Celery broker and JWT revocation |
| Make | any | Optional but recommended |

---

## Local Development Setup

```bash
# 1. Clone
git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git
cd swarmenterprise-v2

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\Activate.ps1         # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Copy environment file and populate it
cp .env.example .env
python scripts/generate_secrets.py   # fills JWT_SECRET_KEY, SECRET_KEY, etc.
# Edit .env — set DATABASE_URL, POSTGRES_PASSWORD, STRIPE_* at minimum

# 5. Apply migrations (SQLite by default for local dev)
alembic upgrade head

# 6. Start the API server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`  
Health check: `http://localhost:8000/health`

---

## Environment Variable Reference

All variables are read from the `.env` file (or shell environment). Copy
`.env.example` for the full annotated template. The table below covers every
variable consumed by the application.

### Critical — Must Be Set Before First Run

| Variable | Description | Example |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | HS256 signing key for access/refresh tokens. Minimum 32 bytes. Generate with `scripts/generate_secrets.py`. | 64-char hex |
| `SECRET_KEY` | General signing key (cookies, CSRF). Minimum 32 bytes. | 64-char hex |
| `ENCRYPTION_KEY` | Symmetric key for encrypting stored PII. 32-byte URL-safe base64. | `generate_secrets.py` output |
| `DATABASE_URL` | Full SQLAlchemy DSN. SQLite for dev; Postgres for staging/prod. | `postgresql+psycopg2://user:pass@localhost:5432/swarm` |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./swarm.db` | Full DB connection string |
| `POSTGRES_HOST` | `postgres` | Postgres hostname (Docker service name) |
| `POSTGRES_DB` | `swarm` | Database name |
| `POSTGRES_USER` | `swarm` | Database user |
| `POSTGRES_PASSWORD` | — | **Required** in production |
| `POSTGRES_PORT` | `5432` | Postgres port |

### Redis / Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `CELERY_BROKER_URL` | `REDIS_URL` | Celery broker (defaults to Redis URL) |
| `CELERY_RESULT_BACKEND` | `REDIS_URL` | Celery result backend |

### Auth

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | placeholder | **Must be changed** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `development` | `development` \| `staging` \| `production` |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `RATE_LIMIT_RPM` | `120` | Max requests per minute per IP |
| `CORS_ORIGINS` | (localhost) | Comma-separated allowed origins |
| `BACKEND_HOST` | `0.0.0.0` | Bind address |
| `BACKEND_PORT` | `8000` | Listen port |

### Stripe

| Variable | Description |
|----------|-------------|
| `STRIPE_API_KEY` | `sk_test_…` (test) or `sk_live_…` (prod) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` from Stripe Dashboard |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_…` or `pk_live_…` |

### Email (SMTP)

| Variable | Description |
|----------|-------------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | `587` (STARTTLS) |
| `SMTP_USER` | SMTP login |
| `SMTP_PASS` | SMTP password |

### LLM / AI

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Default inference model |
| `EMBEDDING_MODEL` | `nomic-embed-text:latest` | Embedding model |

### Observability

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Sentry error-tracking DSN |
| `OTEL_OTLP_ENDPOINT` | OpenTelemetry collector endpoint |
| `OTEL_SDK_DISABLED` | Set `true` to disable OTEL (CI/testing) |

---

## Docker Compose Deployment

### Local development (SQLite, no Postgres)

```bash
docker compose up -d backend redis
```

### Full local stack with Postgres

```bash
docker compose --profile postgres up -d
```

### Rebuild after code changes

```bash
docker compose build backend
docker compose up -d backend
```

### Check service health

```bash
docker compose ps
curl http://localhost:8000/health
```

### Tear down

```bash
docker compose down --volumes
```

### Production deployment

```bash
# Pull latest image
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Start all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile postgres --profile proxy up -d

# Verify
docker compose ps
curl https://api.yourdomain.com/health
```

The entrypoint (`docker-entrypoint.sh`) automatically:
1. Waits for PostgreSQL to be ready (30 attempts, 2 s apart)
2. Checks Redis connectivity
3. Runs `alembic upgrade head`
4. Launches the process passed in `CMD`

---

## Database Migrations

All schema changes are managed through **Alembic**. Migration scripts live in
`alembic/versions/`.

### Apply all pending migrations

```bash
alembic upgrade head
```

### Roll back the last migration

```bash
alembic downgrade -1
```

### Roll back to baseline (empty schema)

```bash
alembic downgrade base
```

### Generate a new migration after model changes

```bash
alembic revision --autogenerate -m "describe the change"
# Review the generated file in alembic/versions/ before applying
alembic upgrade head
```

### Check for unapplied model drift

```bash
alembic check
# Exit code 0 = no drift; non-zero = autogenerate would produce changes
```

### Current migration chain

| Revision | Description |
|----------|-------------|
| `0001` | Initial schema — users, api_keys, company_tenants, deployments, tickets, projects, leads, usage_events, processed_events |
| `0002` | Phase 2 — notifications, message_threads, messages, ticket_history, ticket_comments, workflows, workflow_steps + Phase 2 ticket columns |

---

## Celery Workers and Beat Scheduler

### Start a Celery worker

```bash
celery -A backend.celery_app worker --loglevel=info --queues=default,tickets,notifications
```

### Start the Celery beat scheduler (periodic tasks)

```bash
celery -A backend.celery_app beat --loglevel=info
```

### Periodic task schedule

| Task | Schedule | Queue |
|------|---------|-------|
| `check_sla_breaches` | Every 30 minutes | `high_priority` |
| `escalate_overdue_tickets` | Top of every hour | `high_priority` |

### Monitor with Flower

```bash
celery -A backend.celery_app flower --port=5555
# Open http://localhost:5555
```

---

## Smoke Tests

Run API smoke tests against a running instance:

```bash
# Against local dev server
python scripts/smoke_api.py --base-url http://localhost:8000

# Against a remote environment
python scripts/smoke_api.py --base-url https://api.yourdomain.com \
  --email ops@yourdomain.com --password yourpassword
```

Or via Make:

```bash
make smoke
```

The smoke script tests: register, login, create ticket, read ticket, update
ticket, delete ticket, health check, and logout.

---

## Production Readiness Checklist

Before going live, verify every item below:

### Secrets

- [ ] `JWT_SECRET_KEY` is ≥ 32 bytes of cryptographically random data
- [ ] `SECRET_KEY` is ≥ 32 bytes of cryptographically random data
- [ ] `ENCRYPTION_KEY` is a valid URL-safe base64 32-byte key
- [ ] `POSTGRES_PASSWORD` is a strong random password
- [ ] Stripe live keys are set (`sk_live_…`, `pk_live_…`)
- [ ] `STRIPE_WEBHOOK_SECRET` matches the Stripe Dashboard webhook endpoint
- [ ] All secrets are stored in GitHub Secrets / Vault — not committed to git

### Application

- [ ] `ENV=production` is set
- [ ] `CORS_ORIGINS` is set to your actual domain(s) — no wildcard
- [ ] `LOG_LEVEL=INFO` (not DEBUG)
- [ ] `DRY_RUN_MODE=false` and `TEST_MODE=false`
- [ ] `RATE_LIMIT_RPM` tuned to expected traffic
- [ ] Sentry DSN configured for error tracking

### Database

- [ ] `alembic upgrade head` completed successfully
- [ ] Database backups scheduled (see `scripts/backup_postgres.sh`)
- [ ] Postgres running with persistent volume (not ephemeral container storage)

### Infrastructure

- [ ] TLS certificate provisioned (Let's Encrypt via Caddy or external cert)
- [ ] DNS records pointing to production IP
- [ ] Firewall rules restricting Postgres and Redis to internal network
- [ ] Docker containers running as non-root user (verified in Dockerfile)
- [ ] Resource limits set in docker-compose for each service

### CI/CD

- [ ] GitHub Actions CI passing on `main` branch
- [ ] All GitHub Secrets documented in `.github/SECRETS.md`
- [ ] `dependabot.yml` configured for pip and github-actions

---

## Troubleshooting

### Application fails to start — `JWT_SECRET_KEY must be set`

The startup validator rejects weak or missing keys in non-local environments.
Run `python scripts/generate_secrets.py` and set the output values in your
`.env` or environment.

### `alembic upgrade head` fails with `Target database is not up to date`

Another process holds a migration lock. Check for stale lock rows in
`alembic_version` and clear them if no migration is running:

```sql
DELETE FROM alembic_version;
```

Then re-run `alembic upgrade head`.

### Redis connection refused on startup

The entrypoint waits for Redis but does not abort on failure. Ensure the
`redis` service is up:

```bash
docker compose up -d redis
docker compose exec redis redis-cli ping   # should return PONG
```

### Celery tasks not executing

1. Confirm the worker is running: `celery -A backend.celery_app inspect active`
2. Check broker URL: `echo $CELERY_BROKER_URL`
3. Check queue names match routing config in `backend/celery_app.py`

### `ModuleNotFoundError: No module named 'backend'`

Set `PYTHONPATH=.` before running Python commands:

```bash
PYTHONPATH=. alembic upgrade head
PYTHONPATH=. pytest tests/
```

### Health endpoint returns `"db": "unreachable"`

1. Verify `DATABASE_URL` is correct in `.env`
2. Check Postgres is running: `docker compose ps postgres`
3. Test connectivity: `psql "$DATABASE_URL" -c "SELECT 1"`

---

*Made with IBM Bob*
