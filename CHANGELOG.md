## [v2.0.4] — 2026-06-27


## [v2.0.3] — 2026-06-27


## [v2.0.2] — 2026-06-27


## [v2.0.1] — 2026-06-27


# Changelog — SwarmEnterprise v2

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [2.1.0] — 2025-01-27

### Added

#### `start.sh` — Complete Launch Script
- POSIX-compatible bash script (`set -euo pipefail`) for full service startup.
- **Step 1 — Env validation:** Loads `.env` via `source`, validates `DATABASE_URL` (or `POSTGRES_*` group), `JWT_SECRET_KEY`, and `SECRET_KEY`. Prints actionable error messages and exits 1 on missing vars.
- **Step 2 — Dependency check:** Verifies `docker`, `docker compose` (v2 plugin or v1 `docker-compose`), and `python3` are available; prints install instructions if missing.
- **Step 3 — Docker daemon check:** Confirms `docker info` succeeds before attempting to start containers.
- **Step 4 — Database migrations:** Runs `alembic upgrade head`; exits 1 with diagnostic message on failure.
- **Step 5 — Seed check:** Runs `scripts/seed.py --check`; seeds if not yet seeded. Non-fatal on failure.
- **Step 6 — Service startup:** Starts services via `docker compose` with profile selected by `DEPLOY_PROFILE` (`local`, `staging`, `production`). Includes `docker-compose.prod.yml` overlay in production.
- **Step 7 — Health polling:** Polls `http://localhost:$PORT/health` every 3 seconds for up to 60 seconds; exits 1 on timeout.
- **Step 8 — Summary banner:** Prints all service URLs (API, Docs, Health, Metrics) and operational hints.
- Colour output degrades gracefully when stdout is not a TTY.

#### `stop.sh` — Graceful Shutdown Script
- Sends `SIGTERM` to `swarmOS-backend` and `swarmOS-worker` containers so FastAPI shutdown events and Celery `warm_shutdown` complete.
- Waits 15 seconds for in-flight connections and tasks to drain.
- Runs `docker compose down --remove-orphans` to clean up containers (volumes preserved).
- Prints confirmation banner with restart instructions.
- Resolves compose command (v1/v2) same way as `start.sh`.

#### `scripts/seed.py` — Database Seed Script
- Idempotent seed script safe to run multiple times — all inserts use `ON CONFLICT DO NOTHING`.
- `--check` flag: exits 0 if already seeded, 1 if not (used by `start.sh`).
- `--force` flag: re-seeds even if marked as done.
- Creates a `_seed_meta` sentinel table to track seed state without depending on app table existence.
- Seeds, when tables exist: **roles** (`admin`, `operator`, `viewer`), **admin user** from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars, **ticket categories** (`bug`, `feature`, `task`, `question`), **usage event types** (6 types), **system config** entries (company name, product name, contact email, version, onboarding flag).
- Password hashing: uses `bcrypt` if installed, falls back to PBKDF2-SHA256 (stdlib).
- Gracefully skips tables that don't exist yet (schema may be ahead of seed).
- Company: RWV Techsolutions LLC.

#### `docker-compose.prod.yml` — Production Docker Compose Overlay
- All services from `docker-compose.yml` with production hardening.
- `restart: unless-stopped` on every service.
- **Resource limits** (memory + CPU) and reservations for `backend`, `worker`, `beat`, `redis`, `postgres`, `caddy`, `flower`.
- **Log rotation:** `json-file` driver with `max-size: 20m` / `max-file: 5` (backend, worker, postgres) and smaller limits for support services.
- **Named volumes only** (no bind mounts for persistent data): `pg_data`, `redis_data`, `caddy_data`, `caddy_config`.
- **Network isolation:** `frontend` network (Caddy ↔ backend) and `backend` internal network (backend ↔ postgres ↔ redis ↔ worker). The `backend` network is `internal: true`.
- **Health checks** on every service with appropriate `start_period` values.
- **New `beat` service:** Celery periodic-task scheduler (`celery beat`) under `workers` profile.
- **New `flower` service:** Celery monitoring UI on port 5555 with basic-auth (`FLOWER_USER` / `FLOWER_PASSWORD`), under `workers` profile.
- **Enhanced `redis` service:** AOF persistence (`appendonly yes`, `appendfsync everysec`), `maxmemory 512mb`, `allkeys-lru` eviction policy.
- **Caddy** service includes `PRIMARY_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL` env passthrough and HTTP/3 UDP port.
- All services read from `.env` via `env_file`.

#### `DEPLOYMENT.md` — Full Deployment Guide
- Prerequisites table (Docker, Compose, Python 3.11+, Git, curl).
- 5-step quick start with `make launch`.
- Complete environment variable reference in grouped tables (Domains, Database, Redis, Auth, Admin Seed, LLM Providers, Email/SMTP, Stripe, Telemetry, CORS, Runtime Flags, Flower) with Required/Optional, defaults, and descriptions.
- Production deployment: cloud VM setup commands, SSL with Caddy, Cloudflare Tunnel integration, environment hardening checklist.
- Scaling guide: horizontal Celery workers, PostgreSQL read replicas + PgBouncer, Redis Sentinel.
- Monitoring: built-in `/health` and `/metrics` endpoints, Prometheus + Grafana URLs, Sentry, Flower.
- Troubleshooting section covering 9 common failure modes with diagnostic commands.
- Company: RWV Techsolutions LLC, contact: robertdemottojr50@gmail.com.

#### `CHANGELOG.md` — This File
- Professional changelog documenting all changes in this implementation run.

### Changed

#### `Makefile` — Extended with New Targets
- Added `.PHONY` declarations for all new targets.
- **New targets:** `launch`, `stop`, `status`, `logs`, `seed`, `lint` (updated), `test` (updated), `migrate`, `rollback`, `health`, `smoke`, `clean` (extended), `env-check`.
- `launch` target orchestrates: `env-check` → `migrate` → `seed` → `start.sh` → `smoke`.
- `stop` target delegates to `stop.sh`.
- `status` runs `docker compose ps`.
- `logs` runs `docker compose logs -f` (all services, not just backend).
- `lint` updated to `ruff check --fix . && ruff format .` (replaces `black` + `ruff check`).
- `clean` extended to also run `docker compose down --volumes` and remove `.coverage` / `htmlcov/`.
- `health` inline curl poll of `/health` with pass/fail exit code.
- `smoke` delegates to `scripts/smoke_api.py`.
- `env-check` delegates to `scripts/validate_env.py`.
- All existing targets preserved: `setup`, `install`, `run`, `docker-build`, `docker-up`, `docker-up-wsl`, `docker-up-prod`, `docker-down`, `docker-logs`, `verify`, `heal`, `db-upgrade`, `db-migrate`, `db-downgrade`, `monitoring-up`, `monitoring-down`, `prod-up`, `format`.
- Improved `help` target with aligned, grouped output.

#### `backend/main.py` — Application Enhancements
- **Structured logging setup:** In `production` ENV or when `ENABLE_JSON_LOGGING=true`, configures JSON formatter via `python-json-logger` with `ts`, `level`, `name`, `message`, `request_id` fields. Falls back to plain-text if library missing. Human-readable format retained for local dev.
- **Log level from env:** `LOG_LEVEL` env var (default `INFO`) controls `logging.basicConfig` level.
- **`CorrelationIDMiddleware`:** New `BaseHTTPMiddleware` subclass that reads or generates a UUID v4 `X-Request-ID`, stores it on `request.state.request_id`, and echoes it back on every response header.
- **`on_startup` event:** Validates `JWT_SECRET_KEY` and `SECRET_KEY` are present; logs warnings if missing. Performs a live `SELECT 1` DB connectivity check via SQLAlchemy async engine (`DATABASE_URL`); logs result (non-fatal). Moved outreach worker + lead discovery startup into this event handler (previously at module level).
- **`on_shutdown` event:** Logs shutdown signal receipt, awaits a short `asyncio.sleep(0.5)` to give in-flight coroutines a grace window, logs completion.
- **CORS hardening:** In `production` ENV, if `CORS_ORIGINS` is empty or `*`, logs a warning and sets `allow_origins=[]` (deny all) rather than passing wildcard. Non-production continues to allow `["*"]` fallback.
- Removed unused `import json` side-effect; added `import uuid` and `from starlette.middleware.base import BaseHTTPMiddleware`.
- `startup_discovery` inner function removed; logic moved into unified `on_startup`.

#### `README.md` — Improved Documentation
- Added prominent Quick Start section at top with `make launch` as the single command.
- Added text-based architecture diagram.
- Added links to `DEPLOYMENT.md` and `CHANGELOG.md`.
- All existing content preserved.

---

## [2.0.0] — Prior State (Baseline)

### Existing at time of this implementation run

- FastAPI backend (`backend/main.py`) with Prometheus metrics, CORS, and 10+ API routers.
- `docker-compose.yml` with `backend`, `worker`, `ops-heal`, `redis`, `postgres`, `caddy` services.
- `Makefile` with `setup`, `install`, `test`, `run`, `docker-*`, `db-*`, `monitoring-*`, `prod-up`, `lint`, `format` targets.
- `.env.example` with comprehensive variable documentation.
- `requirements.txt` pinned to stable versions.
- `scripts/validate_env.py` — environment variable validator.
- `scripts/smoke_api.py` — API smoke test suite.
- `scripts/generate_secrets.py` — cryptographic secret generator.
- `scripts/verify_secrets.py` — secrets verification utility.
- Various operational scripts: `backup_postgres.sh`, `restore_postgres.sh`, `run_migrations.sh`, `maintenance.py`, `security_audit.sh`.

---

*SwarmEnterprise v2 — RWV Techsolutions LLC*  
*Contact: robertdemottojr50@gmail.com*