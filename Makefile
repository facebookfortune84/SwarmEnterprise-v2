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

# Cross-platform lowercase: use Python (available everywhere) instead of `tr`
FULL_IMAGE          := $(REGISTRY)/$(shell python -c "print('$(IMAGE_NAME)'.lower())" 2>/dev/null || echo "$(IMAGE_NAME)")

COMPOSE_FILE        := docker-compose.yml
COMPOSE_PROD_FILE   := docker-compose.prod.yml
COMPOSE_ANALYTICS   := docker-compose.analytics.yml
BACKEND_PORT        ?= 8000
ANALYTICS_PORT      ?= 3001
COVERAGE_MIN        ?= 90

# ── Cross-platform Python / pip resolution ────────────────────────────────────
# On Windows prefer .venv\Scripts\python.exe; on Linux prefer .venv/bin/python.
# Fall back to the system `python` / `python3` if .venv does not exist yet.
ifeq ($(OS),Windows_NT)
    VENV_PYTHON     := .venv\Scripts\python.exe
    VENV_PIP        := .venv\Scripts\python.exe -m pip
    VENV_ALEMBIC    := .venv\Scripts\python.exe -m alembic
    VENV_PYTEST     := .venv\Scripts\python.exe -m pytest
    VENV_UVICORN    := .venv\Scripts\python.exe -m uvicorn
    VENV_EXISTS     := $(wildcard .venv\Scripts\python.exe)
    PYTHON_SYS      := python
    # PowerShell is the shell for Windows-specific recipe lines
    SHELL_WIN       := powershell -NoProfile -Command
    PATHSEP         := ;
else
    VENV_PYTHON     := .venv/bin/python
    VENV_PIP        := .venv/bin/python -m pip
    VENV_ALEMBIC    := .venv/bin/python -m alembic
    VENV_PYTEST     := .venv/bin/python -m pytest
    VENV_UVICORN    := .venv/bin/python -m uvicorn
    VENV_EXISTS     := $(wildcard .venv/bin/python)
    PYTHON_SYS      := python3
    PATHSEP         := :
endif

# Use venv Python when available, otherwise system Python
ifneq ($(VENV_EXISTS),)
    PYTHON  := $(VENV_PYTHON)
    PIP     := $(VENV_PIP)
    ALEMBIC := $(VENV_ALEMBIC)
    PYTEST  := $(VENV_PYTEST)
    UVICORN := $(VENV_UVICORN)
else
    PYTHON  := $(PYTHON_SYS)
    PIP     := $(PYTHON_SYS) -m pip
    ALEMBIC := $(PYTHON_SYS) -m alembic
    PYTEST  := $(PYTHON_SYS) -m pytest
    UVICORN := $(PYTHON_SYS) -m uvicorn
endif

# ─────────────────────────────────────────────────────────────────────────────
# .PHONY declarations
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help \
        venv install dev build test test-unit test-e2e lint format \
        migrate rollback seed \
        start stop logs health smoke status clean \
        shell-backend shell-frontend \
        deploy analytics check-docker \
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
	@echo "  SwarmEnterprise v2 -- Build and Operations"
	@echo "  RWV Techsolutions LLC"
	@echo "  ================================================================"
	@echo ""
	@echo "  Core lifecycle"
	@echo "  ----------------------------------------------------------------"
	@echo "  make venv            Create .venv virtual environment"
	@echo "  make install         Install all backend + frontend dependencies"
	@echo "  make dev             Start full dev stack with hot reload"
	@echo "  make build           Build production Docker image"
	@echo "  make start           Launch production stack via docker-compose"
	@echo "  make stop            Graceful shutdown of all services"
	@echo "  make logs            Tail logs from all services"
	@echo "  make health          Health check all running services"
	@echo "  make status          Show running containers"
	@echo "  make clean           Remove build artifacts, caches, temp files"
	@echo ""
	@echo "  Testing"
	@echo "  ----------------------------------------------------------------"
	@echo "  make test            Full test suite + coverage gate (>=90%)"
	@echo "  make test-unit       Unit tests only (fast)"
	@echo "  make test-e2e        End-to-end integration tests"
	@echo "  make smoke           API smoke tests against localhost"
	@echo ""
	@echo "  Code quality"
	@echo "  ----------------------------------------------------------------"
	@echo "  make lint            ruff + black check"
	@echo "  make format          ruff fix + black auto-format"
	@echo "  make env-check       Validate required environment variables"
	@echo ""
	@echo "  Database"
	@echo "  ----------------------------------------------------------------"
	@echo "  make migrate         alembic upgrade head"
	@echo "  make rollback        alembic downgrade -1"
	@echo "  make seed            Populate development seed data"
	@echo "  make db-migrate MSG='...'  Autogenerate migration"
	@echo ""
	@echo "  Shells + deployment"
	@echo "  ----------------------------------------------------------------"
	@echo "  make shell-backend   Open shell in backend container"
	@echo "  make shell-frontend  Open shell in frontend container"
	@echo "  make deploy          Rolling production deployment"
	@echo "  make analytics       Open Umami analytics dashboard"
	@echo ""
	@echo "  Docker shortcuts"
	@echo "  ----------------------------------------------------------------"
	@echo "  make docker-build          docker compose build"
	@echo "  make docker-up             Start local-laptop-ollama stack"
	@echo "  make docker-down           docker compose down"
	@echo "  make docker-up-analytics   Start Umami + its Postgres"
	@echo "  make monitoring-up         Start Prometheus + Grafana"
	@echo "  make prod-up               Full production stack"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# VENV — create isolated virtual environment
# ─────────────────────────────────────────────────────────────────────────────

## Create .venv virtual environment if it does not already exist
venv:
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command \
	  "if (-Not (Test-Path '.venv\Scripts\python.exe')) { \
	    Write-Host '[venv] Creating .venv ...'; \
	    python -m venv .venv; \
	    Write-Host '[venv] Done.' \
	  } else { \
	    Write-Host '[venv] .venv already exists, skipping.' \
	  }"
else
	@if [ ! -f .venv/bin/python ]; then \
	  echo "[venv] Creating .venv ..."; \
	  python3 -m venv .venv; \
	  echo "[venv] Done."; \
	else \
	  echo "[venv] .venv already exists, skipping."; \
	fi
endif

# ─────────────────────────────────────────────────────────────────────────────
# CHECK-DOCKER — preflight guard for all Docker-dependent targets
# ─────────────────────────────────────────────────────────────────────────────

## Verify Docker Desktop / daemon is running; exits 1 with a clear message if not
check-docker:
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command \
	  "docker info 2>&1 | Out-Null; \
	   if ($$LASTEXITCODE -ne 0) { \
	     Write-Error 'ERROR: Docker is not running. Start Docker Desktop and try again.'; \
	     exit 1 \
	   } else { \
	     Write-Host '[check-docker] Docker is running.' \
	   }"
else
	@docker info >/dev/null 2>&1 || \
	  (echo "ERROR: Docker is not running. Start Docker Desktop / dockerd and try again." && exit 1)
	@echo "[check-docker] Docker is running."
endif

# ─────────────────────────────────────────────────────────────────────────────
# INSTALL — all dependencies into .venv
# ─────────────────────────────────────────────────────────────────────────────

## Create .venv (if needed) then install all Python and Node.js dependencies
install: venv
	@echo "[install] Upgrading pip inside .venv ..."
	$(PYTHON) -m pip install --upgrade pip
	@echo "[install] Installing Python dependencies ..."
	$(PIP) install -r requirements.txt
	@echo "[install] Installing Node.js packages ..."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command \
	  "if (Test-Path 'package.json') { npm ci } else { Write-Host '[install] No package.json found, skipping npm.' }"
else
	@if [ -f package.json ]; then npm ci; else echo "[install] No package.json, skipping npm."; fi
endif
	@echo "[install] Done."

# ─────────────────────────────────────────────────────────────────────────────
# DEV — start the full development stack with hot reload
# ─────────────────────────────────────────────────────────────────────────────

## Start full development stack (backend, Redis, analytics) with hot reload
dev: check-docker
	@echo "[dev] Starting development stack ..."
	@echo "[dev]   Backend:   http://localhost:$(BACKEND_PORT)"
	@echo "[dev]   Analytics: http://localhost:$(ANALYTICS_PORT)"
	@echo "[dev]   API Docs:  http://localhost:$(BACKEND_PORT)/docs"
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_ANALYTICS) \
	  up -d redis umami-db umami
	$(UVICORN) backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

# ─────────────────────────────────────────────────────────────────────────────
# BUILD — production builds
# ─────────────────────────────────────────────────────────────────────────────

## Build production frontend assets and backend Docker image
build: check-docker
	@echo "[build] Building backend Docker image ..."
	docker build \
	  -f backend/Dockerfile \
	  -t $(FULL_IMAGE):$(IMAGE_TAG) \
	  -t $(FULL_IMAGE):latest \
	  --build-arg VCS_REF=$(IMAGE_TAG) \
	  .
	@echo "[build] Backend image: $(FULL_IMAGE):$(IMAGE_TAG)"
	@echo "[build] Frontend assets are static HTML/JS -- no build step required."
	@echo "[build] Build complete."

# ─────────────────────────────────────────────────────────────────────────────
# TEST — full suite with coverage gate
# ─────────────────────────────────────────────────────────────────────────────

## Run full test suite with coverage reporting and enforce >=90% gate
test:
	$(PYTEST) tests/ \
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
	@echo "[test] Coverage gate: >=$(COVERAGE_MIN)%"

## Run unit tests only (fast, no integration dependencies)
test-unit:
	$(PYTEST) tests/ \
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
	@echo "[test-e2e] Running sovereign integration tests ..."
	$(PYTEST) \
	  tests_sovereign/test_db_integration.py \
	  tests_sovereign/test_factory_orchestration.py \
	  tests_sovereign/test_api.py \
	  tests_sovereign/test_workflow_service.py \
	  -v --tb=short

# ─────────────────────────────────────────────────────────────────────────────
# LINT — backend and frontend linters
# ─────────────────────────────────────────────────────────────────────────────

## Run all linters (ruff + black; no auto-fix)
lint:
	@echo "[lint] ruff check ..."
	$(PYTHON) -m ruff check .
	@echo "[lint] black format check ..."
	$(PYTHON) -m black --check .
	@echo "[lint] All lint checks passed."

## Auto-format: ruff fix + black
format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .
	$(PYTHON) -m black .

## Check formatting without modifying files
format-check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m black --check .

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

## Run alembic upgrade head (cross-platform via scripts/run_alembic.py)
migrate:
	$(PYTHON) scripts/run_alembic.py upgrade head

## Run alembic downgrade -1
rollback:
	$(PYTHON) scripts/run_alembic.py downgrade -1

## Populate development seed data
seed:
	$(PYTHON) scripts/seed.py

## Autogenerate a new Alembic migration (usage: make db-migrate MSG="add users table")
db-migrate:
	$(PYTHON) scripts/run_alembic.py revision --autogenerate -m "$(MSG)"

## Alias: alembic upgrade head
db-upgrade:
	$(PYTHON) scripts/run_alembic.py upgrade head

## Alias: alembic downgrade -1
db-downgrade:
	$(PYTHON) scripts/run_alembic.py downgrade -1

# ─────────────────────────────────────────────────────────────────────────────
# SERVICE LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

## Full launch sequence: env-check -> migrate -> seed -> start -> smoke
launch: env-check check-docker
	@echo "[launch] Running database migrations ..."
	$(MAKE) migrate
	@echo "[launch] Seeding initial data ..."
	$(MAKE) seed
	@echo "[launch] Starting services ..."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command "bash start.sh 2>$$null; if (Test-Path start.sh) { bash start.sh } else { docker compose -f $(COMPOSE_FILE) up -d }"
else
	bash start.sh
endif
	@echo "[launch] Running smoke tests ..."
	$(MAKE) smoke
	@echo ""
	@echo "[launch] All systems go. SwarmEnterprise v2 is live."
	@echo "[launch]    API:       http://localhost:$(BACKEND_PORT)"
	@echo "[launch]    Dashboard: http://localhost:$(BACKEND_PORT)/dashboard/"
	@echo "[launch]    Analytics: http://localhost:$(ANALYTICS_PORT)"

## Launch production stack via docker-compose (services only, no migrations)
start: check-docker
	@echo "[start] Starting production stack ..."
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  up -d --remove-orphans
	@echo "[start] Services started."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command "Start-Sleep -Seconds 5"
else
	@sleep 5
endif
	$(MAKE) health

## Graceful shutdown of all services
stop:
	@echo "[stop] Stopping all services ..."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command \
	  "if (Test-Path 'stop.sh') { bash stop.sh } else { docker compose -f $(COMPOSE_FILE) down }"
else
	bash stop.sh
endif

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
	$(PYTHON) scripts/run_health_check.py $(BACKEND_PORT) $(ANALYTICS_PORT)

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

## Open an interactive shell in the frontend container (static -- opens backend)
shell-frontend:
	@echo "[shell-frontend] Frontend is static HTML served by FastAPI/Caddy."
	@echo "[shell-frontend] Opening backend shell instead ..."
	$(MAKE) shell-backend

# ─────────────────────────────────────────────────────────────────────────────
# DEPLOY — production deployment
# ─────────────────────────────────────────────────────────────────────────────

## Trigger a production deployment via docker-compose rolling update
deploy: check-docker
	@echo "[deploy] Pulling latest image ..."
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  pull
	@echo "[deploy] Rolling deployment ..."
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  up -d --remove-orphans --pull always
	@echo "[deploy] Running post-deploy health check ..."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command "Start-Sleep -Seconds 10"
else
	@sleep 10
endif
	$(MAKE) health
	@echo "[deploy] Deployment complete."

# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────

## Open the Umami analytics dashboard in the default browser
analytics:
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command "Start-Process 'http://localhost:$(ANALYTICS_PORT)'"
	@echo "[analytics] Opened http://localhost:$(ANALYTICS_PORT)"
else
	@URL="http://localhost:$(ANALYTICS_PORT)"; \
	echo "[analytics] Opening $$URL"; \
	if command -v xdg-open >/dev/null 2>&1; then xdg-open "$$URL"; \
	elif command -v open >/dev/null 2>&1; then open "$$URL"; \
	else echo "[analytics] Open $$URL in your browser"; fi
endif

# ─────────────────────────────────────────────────────────────────────────────
# CLEAN — remove build artifacts, caches, and temp files
# ─────────────────────────────────────────────────────────────────────────────

## Remove all build artifacts, caches, and temporary files
clean:
	@echo "[clean] Removing Docker containers and volumes ..."
	-docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans 2>/dev/null
	-docker compose -f $(COMPOSE_ANALYTICS) down --volumes --remove-orphans 2>/dev/null
	@echo "[clean] Removing Python caches ..."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command \
	  "Get-ChildItem -Recurse -Include '__pycache__','.pytest_cache','.ruff_cache' -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; \
	   Get-ChildItem -Recurse -Filter '*.pyc' | Remove-Item -Force -ErrorAction SilentlyContinue; \
	   Remove-Item -Recurse -Force 'build','dist','htmlcov' -ErrorAction SilentlyContinue; \
	   Remove-Item -Force 'coverage.xml','.coverage' -ErrorAction SilentlyContinue; \
	   Get-ChildItem -Filter '*.egg-info' -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
else
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) \
	  -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ coverage.xml coverage_*.xml
endif
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

docker-build: check-docker
	docker compose -f $(COMPOSE_FILE) build

docker-up: check-docker
	docker compose \
	  -f $(COMPOSE_FILE) \
	  up -d

docker-up-wsl: check-docker
	docker compose -f $(COMPOSE_FILE) -f docker-compose.wsl-docker.yml up -d

docker-up-prod: check-docker
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile postgres --profile proxy --profile workers \
	  up -d

## Start analytics stack (Umami + its Postgres)
docker-up-analytics: check-docker
	@echo "[analytics] Starting Umami analytics stack ..."
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_ANALYTICS) \
	  up -d umami-db umami
	@echo "[analytics] Waiting for Umami to start (20s) ..."
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -Command "Start-Sleep -Seconds 20"
else
	@sleep 20
endif
	@echo "[analytics] Umami dashboard: http://localhost:$(ANALYTICS_PORT)"
	@echo "[analytics] Default login:   admin / umami   (change on first login!)"

docker-down:
	docker compose -f $(COMPOSE_FILE) down

docker-logs:
	docker compose -f $(COMPOSE_FILE) logs -f backend

monitoring-up: check-docker
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f deploy/docker/docker-compose.monitoring.yml \
	  up -d

monitoring-down:
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f deploy/docker/docker-compose.monitoring.yml \
	  down

prod-up: check-docker
	docker compose \
	  -f $(COMPOSE_FILE) \
	  -f $(COMPOSE_PROD_FILE) \
	  --profile ops --profile postgres --profile proxy --profile workers \
	  up -d

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

setup:
	bash setup.sh

run:
	$(UVICORN) backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

verify:
	$(PYTHON) scripts/verify_secrets.py

heal:
	$(PYTHON) -c "from agents.ops.self_heal import run_heal_cycle; run_heal_cycle()"
