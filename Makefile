# SwarmEnterprise v2 — Makefile
# RWV Techsolutions LLC · robertdemottojr50@gmail.com
# ─────────────────────────────────────────────────────────────────────────────
#
# VARIABLES — override at the command line or in .env
# ─────────────────────────────────────────────────────────────────────────────

ENV                 ?= development
REGISTRY            ?= ghcr.io
IMAGE_NAME          ?= swarmenterprise-backend
IMAGE_TAG           ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
FULL_IMAGE          := $(REGISTRY)/$(shell echo "$(IMAGE_NAME)" | tr '[:upper:]' '[:lower:]')
COMPOSE_FILE        := docker-compose.yml
COMPOSE_PROD_FILE   := docker-compose.prod.yml
COMPOSE_ANALYTICS   := docker-compose.analytics.yml
BACKEND_PORT        ?= 8000
ANALYTICS_PORT      ?= 3001
COVERAGE_MIN        ?= 90
PYTHON              ?= python
PIP                 ?= pip

# ─────────────────────────────────────────────────────────────────────────────
# .PHONY declarations
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help \
        install dev build test test-unit test-e2e lint format \
        migrate rollback seed \
        start stop logs health smoke status clean \
        shell-backend shell-frontend \
        deploy analytics \
        env-check verify \
        launch \
        docker-build docker-up docker-down docker-logs \
        docker-up-wsl docker-up-prod docker-up-analytics \
        monitoring-up monitoring-down prod-up \
        db-upgrade db-migrate db-downgrade \
        heal setup run format-check

# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT: help
# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  SwarmEnterprise v2 — Build & Operations"
	@echo "  RWV Techsolutions LLC"
	@echo "  ════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Core lifecycle"
	@echo "  ────────────────────────────────────────────────────────────────"
	@printf "  %-28s %s\n" "make install"       "Install all backend + frontend dependencies"
	@printf "  %-28s %s\n" "make dev"            "Start full dev stack (backend, Redis, analytics)"
	@printf "  %-28s %s\n" "make build"          "Build production frontend bundle + backend Docker image"
	@printf "  %-28s %s\n" "make start"          "Launch production stack via docker-compose"
	@printf "  %-28s %s\n" "make stop"           "Graceful shutdown of all services"
	@printf "  %-28s %s\n" "make logs"           "Tail logs from all services (Ctrl-C to exit)"
	@printf "  %-28s %s\n" "make health"         "Health check all running services and report status"
	@printf "  %-28s %s\n" "make status"         "Show running containers and their health"
	@printf "  %-28s %s\n" "make clean"          "Remove build artifacts, caches, and temp files"
	@echo ""
	@echo "  Testing"
	@echo "  ────────────────────────────────────────────────────────────────"
	@printf "  %-28s %s\n" "make test"           "Run full test suite with coverage (≥${COVERAGE_MIN}% gate)"
	@printf "  %-28s %s\n" "make test-unit"      "Run unit tests only (fast, no integration)"
	@printf "  %-28s %s\n" "make test-e2e"       "Run end-to-end tests against running stack"
	@printf "  %-28s %s\n" "make smoke"          "Run API smoke tests against localhost"
	@echo ""
	@echo "  Code quality"
	@echo "  ────────────────────────────────────────────────────────────────"
	@printf "  %-28s %s\n" "make lint"           "Run ruff check + black (backend) + ESLint (frontend)"
	@printf "  %-28s %s\n" "make format"         "Auto-format: ruff format + black"
	@printf "  %-28s %s\n" "make env-check"      "Validate all required environment variables"
	@echo ""
	@echo "  Database"
	@echo "  ────────────────────────────────────────────────────────────────"
	@printf "  %-28s %s\n" "make migrate"        "Run alembic upgrade head"
	@printf "  %-28s %s\n" "make rollback"       "Run alembic downgrade -1"
	@printf "  %-28s %s\n" "make seed"           "Populate development seed data"
	@printf "  %-28s %s\n" "make db-migrate MSG='…'" "Autogenerate a new migration"
	@echo ""
	@echo "  Shells + deployment"
	@echo "  ────────────────────────────────────────────────────────────────"
	@printf "  %-28s %s\n" "make shell-backend"  "Open interactive shell in backend container"
	@printf "  %-28s %s\n" "make shell-frontend" "Open interactive shell in frontend container (if any)"
	@printf "  %-28s %s\n" "make deploy"         "Trigger production deployment via SSH"
	@printf "  %-28s %s\n" "make analytics"      "Open the Umami analytics dashboard URL"
	@echo ""
	@echo "  Legacy shortcuts (docker compose)"
	@echo "  ────────────────────────────────────────────────────────────────"
	@printf "  %-28s %s\n" "make docker-build"   "docker-compose build"
	@printf "  %-28s %s\n" "make docker-up"      "Start local-laptop-ollama stack"
	@printf "  %-28s %s\n" "make docker-down"    "docker compose down"
	@printf "  %-28s %s\n" "make monitoring-up"  "Start Prometheus + Grafana monitoring stack"
	@printf "  %-28s %s\n" "make prod-up"        "Full production stack"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# INSTALL — all dependencies
# ─────────────────────────────────────────────────────────────────────────────

## Install all backend and frontend dependencies
install:
	@echo "[install] Installing Python dependencies…"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "[install] Installing Node.js packages (root)…"
	@if [ -f package.json ]; then npm install; fi
	@echo "[install] Done."

# ─────────────────────────────────────────────────────────────────────────────
# DEV — start the full development stack with hot reload
# ─────────────────────────────────────────────────────────────────────────────

## Start full development stack (backend, Redis, analytics) with hot reload
dev:
	@echo "[dev] Starting development stack…"
	@echo "[dev]   Backend:   http://localhost:${BACKEND_PORT}"
	@echo "[dev]   Analytics: http://localhost:${ANALYTICS_PORT}"
	@echo "[dev]   API Docs:  http://localhost:${BACKEND_PORT}/docs"
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_ANALYTICS) \
	  up -d redis umami-db umami
	$(PYTHON) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

# ─────────────────────────────────────────────────────────────────────────────
# BUILD — production builds
# ─────────────────────────────────────────────────────────────────────────────

## Build production frontend assets and backend Docker image
build:
	@echo "[build] Building backend Docker image…"
	docker build \
	  -f backend/Dockerfile \
	  -t $(FULL_IMAGE):$(IMAGE_TAG) \
	  -t $(FULL_IMAGE):latest \
	  --build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ") \
	  --build-arg VCS_REF=$(IMAGE_TAG) \
	  .
	@echo "[build] Backend image: $(FULL_IMAGE):$(IMAGE_TAG)"
	@echo "[build] Frontend assets are static HTML/JS — no build step required."
	@echo "[build] Build complete."

# ─────────────────────────────────────────────────────────────────────────────
# TEST — full suite with coverage gate
# ─────────────────────────────────────────────────────────────────────────────

## Run full test suite with coverage reporting and enforce ≥90% gate
test:
	pytest tests/ \
	  --ignore=tests/test_main_coverage.py \
	  --ignore=tests/test_live_factory.py \
	  --ignore=tests/test_live_marketing.py \
	  -v --tb=short \
	  --cov=backend \
	  --cov=agents \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov \
	  --cov-report=xml:coverage.xml \
	  --cov-fail-under=$(COVERAGE_MIN)
	@echo "[test] Coverage gate: ≥$(COVERAGE_MIN)% ✅"

## Run unit tests only (fast, no integration dependencies)
test-unit:
	pytest tests/ \
	  --ignore=tests/test_main_coverage.py \
	  --ignore=tests/test_live_factory.py \
	  --ignore=tests/test_live_marketing.py \
	  --ignore=tests/test_commander.py \
	  --ignore=tests/test_company_generator.py \
	  --ignore=tests/test_deployment_service.py \
	  -v --tb=short \
	  --cov=backend \
	  --cov-report=term-missing \
	  -q

## Run end-to-end tests against the running stack
test-e2e:
	@echo "[test-e2e] Running sovereign integration tests…"
	pytest \
	  tests_sovereign/test_db_integration.py \
	  tests_sovereign/test_factory_orchestration.py \
	  tests_sovereign/test_api.py \
	  tests_sovereign/test_workflow_service.py \
	  -v --tb=short

# ─────────────────────────────────────────────────────────────────────────────
# LINT — backend and frontend linters
# ─────────────────────────────────────────────────────────────────────────────

## Run all linters (ruff + black for backend; reports only — no auto-fix)
lint:
	@echo "[lint] ruff check…"
	ruff check .
	@echo "[lint] black format check…"
	black --check .
	@echo "[lint] All lint checks passed."

## Auto-format: ruff format + black
format:
	ruff check --fix .
	ruff format .
	black .

## Check formatting without modifying files
format-check:
	ruff check .
	ruff format --check .
	black --check .

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

## Run alembic upgrade head
migrate:
	alembic upgrade head

## Run alembic downgrade -1
rollback:
	alembic downgrade -1

## Populate development seed data
seed:
	$(PYTHON) scripts/seed.py

## Autogenerate a new Alembic migration (usage: make db-migrate MSG="add users table")
db-migrate:
	alembic revision --autogenerate -m "$(MSG)"

## Alias: alembic upgrade head
db-upgrade:
	alembic upgrade head

## Alias: alembic downgrade -1
db-downgrade:
	alembic downgrade -1

# ─────────────────────────────────────────────────────────────────────────────
# SERVICE LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

## Launch full production stack (validate → migrate → seed → start → health)
launch: env-check
	@echo "[launch] Running database migrations…"
	$(MAKE) migrate
	@echo "[launch] Seeding initial data…"
	$(MAKE) seed
	@echo "[launch] Starting services…"
	bash start.sh
	@echo "[launch] Running smoke tests…"
	$(MAKE) smoke
	@echo ""
	@echo "[launch] ✅ All systems go. SwarmEnterprise v2 is live."
	@echo "[launch]    API:       http://localhost:$(BACKEND_PORT)"
	@echo "[launch]    Dashboard: http://localhost:$(BACKEND_PORT)/dashboard/"
	@echo "[launch]    Analytics: http://localhost:$(ANALYTICS_PORT)"

## Launch production stack via docker-compose (services only, no migrations)
start:
	@echo "[start] Starting production stack…"
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  up -d --remove-orphans
	@echo "[start] Services started. Running health check…"
	@sleep 5
	$(MAKE) health

## Graceful shutdown of all services
stop:
	@echo "[stop] Stopping all services…"
	bash stop.sh

## Show status of all services and their health
status:
	docker compose -f $(COMPOSE_FILE) ps

## Tail logs from all services (Ctrl-C to exit)
logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH — check all running services
# ─────────────────────────────────────────────────────────────────────────────

## Perform a health check against all running services and report status
health:
	@echo ""
	@echo "  SwarmOS Health Check"
	@echo "  ──────────────────────────────────────────────────────────────"
	@PORT=$(BACKEND_PORT); \
	URL="http://localhost:$${PORT}/health"; \
	echo "  Checking $${URL}…"; \
	RESULT=$$(curl -sf "$${URL}" 2>/dev/null); \
	if [ -n "$$RESULT" ]; then \
	  echo "  ✅ Backend:   ONLINE"; \
	  echo "     $$(echo $$RESULT | python -c 'import sys,json; d=json.load(sys.stdin); print(\"version=\"+d.get(\"version\",\"?\"),\"| db=\"+d.get(\"checks\",{}).get(\"db\",\"?\"),\"| redis=\"+d.get(\"checks\",{}).get(\"redis\",\"?\"))' 2>/dev/null || echo "$$RESULT")"; \
	else \
	  echo "  ❌ Backend:   UNREACHABLE (is it running? try: make start)"; \
	fi
	@REDIS_STATUS=$$(docker compose -f $(COMPOSE_FILE) ps --format json redis 2>/dev/null | python -c 'import sys,json; d=[l for l in sys.stdin if l.strip()]; r=json.loads(d[0]) if d else {}; print(r.get("Health","unknown"))' 2>/dev/null || echo "unknown"); \
	if [ "$$REDIS_STATUS" = "healthy" ]; then \
	  echo "  ✅ Redis:     healthy"; \
	else \
	  echo "  ⚠️  Redis:     $$REDIS_STATUS"; \
	fi
	@ANALYTICS_STATUS=$$(curl -sf "http://localhost:$(ANALYTICS_PORT)/api/heartbeat" 2>/dev/null && echo "online" || echo "offline"); \
	if [ "$$ANALYTICS_STATUS" = "online" ]; then \
	  echo "  ✅ Analytics: http://localhost:$(ANALYTICS_PORT)"; \
	else \
	  echo "  ⚠️  Analytics: offline (start with: make docker-up-analytics)"; \
	fi
	@echo ""

## Run API smoke tests against localhost
smoke:
	$(PYTHON) scripts/smoke_api.py --base-url http://localhost:$(BACKEND_PORT)

# ─────────────────────────────────────────────────────────────────────────────
# SHELLS
# ─────────────────────────────────────────────────────────────────────────────

## Open an interactive shell in the backend container
shell-backend:
	docker compose -f $(COMPOSE_FILE) exec backend /bin/bash || \
	docker compose -f $(COMPOSE_FILE) exec backend /bin/sh

## Open an interactive shell in the frontend container (static — opens bash in backend)
shell-frontend:
	@echo "[shell-frontend] Frontend is static HTML served by FastAPI/Caddy."
	@echo "[shell-frontend] Opening backend shell instead…"
	$(MAKE) shell-backend

# ─────────────────────────────────────────────────────────────────────────────
# DEPLOY — production deployment
# ─────────────────────────────────────────────────────────────────────────────

## Trigger a production deployment via docker-compose rolling update
deploy:
	@echo "[deploy] Pulling latest image…"
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  pull
	@echo "[deploy] Rolling deployment…"
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  up -d --remove-orphans --pull always
	@echo "[deploy] Running post-deploy health check…"
	@sleep 10
	$(MAKE) health
	@echo "[deploy] ✅ Deployment complete."

# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

## Open the Umami analytics dashboard in the default browser
analytics:
	@URL="http://localhost:$(ANALYTICS_PORT)"; \
	echo "[analytics] Opening $$URL"; \
	if command -v xdg-open >/dev/null 2>&1; then \
	  xdg-open "$$URL"; \
	elif command -v open >/dev/null 2>&1; then \
	  open "$$URL"; \
	elif command -v start >/dev/null 2>&1; then \
	  start "$$URL"; \
	else \
	  echo "[analytics] Open $$URL in your browser"; \
	fi

# ─────────────────────────────────────────────────────────────────────────────
# CLEAN — remove build artifacts, caches, and temp files
# ─────────────────────────────────────────────────────────────────────────────

## Remove all build artifacts, caches, and temporary files
clean:
	@echo "[clean] Removing Docker containers and volumes…"
	docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans 2>/dev/null || true
	docker compose -f $(COMPOSE_ANALYTICS) down --volumes --remove-orphans 2>/dev/null || true
	@echo "[clean] Removing Python caches…"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "[clean] Removing coverage and build artifacts…"
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ coverage.xml coverage_*.xml
	@echo "[clean] Done."

# ─────────────────────────────────────────────────────────────────────────────
# ENV CHECK
# ─────────────────────────────────────────────────────────────────────────────

## Validate all required environment variables
env-check:
	$(PYTHON) scripts/validate_env.py

# ─────────────────────────────────────────────────────────────────────────────
# DOCKER COMPOSE SHORTCUTS
# ─────────────────────────────────────────────────────────────────────────────

docker-build:
	docker compose -f $(COMPOSE_FILE) build

docker-up:
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f docker-compose.local-laptop-ollama.yml 2>/dev/null \
	  up -d || \
	docker compose -f $(COMPOSE_FILE) up -d

docker-up-wsl:
	docker compose -f $(COMPOSE_FILE) -f docker-compose.wsl-docker.yml up -d

docker-up-prod:
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  up -d

## Start analytics stack (Umami + its Postgres)
docker-up-analytics:
	@echo "[analytics] Starting Umami analytics stack…"
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_ANALYTICS) \
	  up -d umami-db umami
	@echo "[analytics] Waiting for Umami to start (20s)…"
	@sleep 20
	@echo "[analytics] Umami dashboard: http://localhost:$(ANALYTICS_PORT)"
	@echo "[analytics] Default login:   admin / umami   (change on first login!)"

docker-down:
	docker compose -f $(COMPOSE_FILE) down

docker-logs:
	docker compose -f $(COMPOSE_FILE) logs -f backend

monitoring-up:
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f deploy/docker/docker-compose.monitoring.yml \
	  up -d

monitoring-down:
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f deploy/docker/docker-compose.monitoring.yml \
	  down

prod-up:
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  -f deploy/docker/docker-compose.monitoring.yml 2>/dev/null \
	  --profile ops --profile postgres --profile proxy --profile workers \
	  up -d

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

setup:
	bash setup.sh

run:
	$(PYTHON) -m uvicorn backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

verify:
	$(PYTHON) scripts/verify_secrets.py

heal:
	$(PYTHON) -c "from agents.ops.self_heal import run_heal_cycle; run_heal_cycle()"
