# Launch Guide — SwarmEnterprise v2

**Company:** RWV Techsolutions LLC  
**Contact:** robertdemottojr50@gmail.com  
**Address:** 1091 Harrison Ave, Elkins, WV 26241, USA

---

## Single-Command Launch

```bash
make launch
```

This single command performs the complete launch sequence: environment validation → Docker build → database migrations → data seeding → service startup → health checks → smoke tests → status summary.

---

## Pre-Launch Checklist

Before running `make launch`, complete these steps:

### Step 1 — Copy and fill environment file

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | Or set `POSTGRES_*` vars |
| `JWT_SECRET_KEY` | Yes | Generate: `python scripts/generate_secrets.py` |
| `SECRET_KEY` | Yes | Generate: `python scripts/generate_secrets.py` |
| `ADMIN_EMAIL` | Yes | Email for the initial admin account |
| `ADMIN_PASSWORD` | Yes | Strong password — change after first login |
| `STRIPE_API_KEY` | For payments | Use `sk_test_...` in development |
| `STRIPE_WEBHOOK_SECRET` | For payments | From Stripe Dashboard |
| `SMTP_SERVER` | For emails | See [docs/SECRETS.md](SECRETS.md#5-smtp-email) |
| `SMTP_USER` | For emails | |
| `SMTP_PASS` | For emails | |

For complete variable documentation see [docs/SECRETS.md](SECRETS.md).

### Step 2 — Validate environment

```bash
make env-check
# or directly:
python scripts/validate_env.py
```

All required variables must show `[OK]` before proceeding.

### Step 3 — Check Docker is running

```bash
docker info
```

On Windows with WSL, ensure Docker Desktop is running and WSL integration is enabled.

---

## Launch Sequence (What `make launch` Does)

The launch target in `Makefile` runs `./start.sh` which executes these phases in order:

| Phase | What Happens | Failure Action |
|-------|-------------|----------------|
| 1 | Load `.env` and validate required variables | Exit 1 with missing var name |
| 2 | Check dependencies: `docker`, `docker compose`, `python3` | Exit 1 with install instructions |
| 3 | Verify Docker daemon is running | Exit 1 with instructions |
| 4 | Run `alembic upgrade head` (database migrations) | Exit 1 with migration error |
| 5 | Run `python scripts/seed.py` (initial data) | Warning only (non-fatal) |
| 6 | Run `docker compose up -d --build` | Exit 1 with compose error |
| 7 | Poll `GET /health` every 3 seconds, 60s timeout | Exit 1 on timeout |
| 8 | Print service URLs and status summary | — |

---

## Manual Launch (Step by Step)

If you prefer step-by-step control:

```bash
# 1. Validate environment
python scripts/validate_env.py

# 2. Run migrations
make migrate
# or: alembic upgrade head

# 3. Seed initial data
make seed
# or: python scripts/seed.py

# 4. Start services (development)
make docker-up
# or: docker compose up -d

# 5. Start services (production with all profiles)
make prod-up
# or: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 6. Check service health
make health
# or: curl http://localhost:8000/health

# 7. Run smoke tests
make smoke
# or: python scripts/smoke_api.py
```

---

## Service URLs

After a successful launch, the following services are available:

| Service | URL | Notes |
|---------|-----|-------|
| **API (direct)** | http://localhost:8000 | FastAPI backend |
| **API via Caddy** | https://yourdomain.com/api | Via reverse proxy |
| **Swagger UI** | http://localhost:8000/docs | Interactive API docs |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |
| **Health check** | http://localhost:8000/health | Service status |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |
| **Grafana** | http://localhost:3000 | Monitoring dashboard |
| **Prometheus** | http://localhost:9090 | Metrics scraper |
| **Celery Flower** | http://localhost:5555 | Task queue monitor |
| **Alertmanager** | http://localhost:9093 | Alert routing |

---

## Stopping the Application

```bash
make stop
# or: ./stop.sh
```

This sends SIGTERM to running containers, waits 15 seconds for connection drain, then runs `docker compose down`.

For immediate hard stop:

```bash
docker compose down
```

---

## Logs

```bash
# Tail all service logs
make logs

# Single service
docker compose logs -f backend
docker compose logs -f worker
```

---

## Status Check

```bash
make status
```

Shows running containers, their health status, and resource usage.

---

## Smoke Tests

After launch, run the full smoke test suite to verify all critical paths:

```bash
make smoke
# or: python scripts/smoke_api.py
# or: ./scripts/smoke_test.sh http://localhost:8000
```

Expected output: all tests PASS with HTTP 200/201 responses.

---

## Troubleshooting

### Port already in use
```bash
docker compose down
# or kill process on port:
# Windows: netstat -ano | findstr :8000  then  taskkill /PID <pid> /F
```

### Database connection failed
- Check `DATABASE_URL` or `POSTGRES_*` variables are set correctly
- Verify Postgres container is running: `docker compose ps`
- Check Postgres logs: `docker compose logs postgres`

### Alembic migration failed
```bash
# Check current revision
alembic current
# Try again
alembic upgrade head
# See migration history
alembic history
```

### Services not starting
```bash
# View all container statuses
docker compose ps -a
# View logs for failing service
docker compose logs <service-name>
```

### Health check timeout
- Services may take longer than 60 seconds on first build
- Increase timeout: `HEALTH_TIMEOUT=120 ./start.sh`
- Check if the backend port is exposed: `docker compose ps backend`

---

## Production Deployment

For a complete production deployment guide including SSL, Cloudflare, firewall hardening, and scaling, see:

- [DEPLOYMENT.md](../DEPLOYMENT.md) — full deployment reference
- [docs/guides/SECURITY_HARDENING.md](guides/SECURITY_HARDENING.md) — security configuration
- [docs/guides/SCALING_GUIDE.md](guides/SCALING_GUIDE.md) — horizontal scaling
- [docs/guides/DISASTER_RECOVERY.md](guides/DISASTER_RECOVERY.md) — DR runbook

---

*RWV Techsolutions LLC — 1091 Harrison Ave, Elkins, WV 26241 — robertdemottojr50@gmail.com*
