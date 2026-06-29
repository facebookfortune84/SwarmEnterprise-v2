# SwarmEnterprise v2 — Makefile
# RWV Techsolutions LLC · robertdemottojr50@gmail.com
# =============================================================================
#
# VARIABLES — override at the command line or via environment
# =============================================================================

ENV                 ?= development
REGISTRY            ?= ghcr.io
IMAGE_NAME          ?= swarmenterprise-backend
IMAGE_TAG           ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

# Cross-platform lowercase — uses Python so `tr` is never needed on Windows.
FULL_IMAGE          := $(REGISTRY)/$(shell python -c "print('$(IMAGE_NAME)'.lower())" 2>/dev/null || echo $(IMAGE_NAME))

COMPOSE_FILE        := docker-compose.yml
COMPOSE_PROD_FILE   := docker-compose.prod.yml
COMPOSE_ANALYTICS   := docker-compose.analytics.yml
BACKEND_PORT        ?= 8000
ANALYTICS_PORT      ?= 3001
COVERAGE_MIN        ?= 90

# =============================================================================
# Cross-platform Python / pip / tool resolution
#   Windows: .venv\Scripts\python.exe   Linux/macOS: .venv/bin/python
#   Falls back to system python / python3 when .venv does not exist yet.
# =============================================================================
ifeq ($(OS),Windows_NT)
    VENV_PYTHON  := .venv\Scripts\python.exe
    VENV_EXISTS  := $(wildcard .venv\Scripts\python.exe)
    PYTHON_SYS   := python
else
    VENV_PYTHON  := .venv/bin/python
    VENV_EXISTS  := $(wildcard .venv/bin/python)
    PYTHON_SYS   := python3
endif

ifneq ($(VENV_EXISTS),)
    PYTHON   := $(VENV_PYTHON)
else
    PYTHON   := $(PYTHON_SYS)
endif

PIP     := $(PYTHON) -m pip
PYTEST  := $(PYTHON) -m pytest
UVICORN := $(PYTHON) -m uvicorn

# =============================================================================
# .PHONY declarations
# =============================================================================
.PHONY: help \
        venv install dev build test test-unit test-e2e lint format format-check \
        migrate rollback seed db-upgrade db-migrate db-downgrade \
        start stop logs health smoke status clean \
        shell-backend shell-frontend \
        deploy analytics check-docker \
        env-check verify launch \
        docker-build docker-up docker-down docker-logs \
        docker-up-wsl docker-up-prod docker-up-analytics \
        monitoring-up monitoring-down prod-up \
        heal setup run

# =============================================================================
# help — default target
# =============================================================================
help:
	@echo.
	@echo   SwarmEnterprise v2 -- Build and Operations
	@echo   RWV Techsolutions LLC
	@echo   ================================================================
	@echo.
	@echo   Core lifecycle
	@echo   ----------------------------------------------------------------
	@echo   make venv            Create .venv virtual environment
	@echo   make install         Install all backend + frontend dependencies
	@echo   make dev             Start full dev stack with hot reload
	@echo   make build           Build production Docker image
	@echo   make start           Launch production stack via docker-compose
	@echo   make stop            Graceful shutdown of all services
	@echo   make logs            Tail logs from all services
	@echo   make health          Health check all running services
	@echo   make status          Show running containers
	@echo   make clean           Remove build artifacts, caches, temp files
	@echo.
	@echo   Testing
	@echo   ----------------------------------------------------------------
	@echo   make test            Full test suite + coverage gate
	@echo   make test-unit       Unit tests only
	@echo   make test-e2e        End-to-end integration tests
	@echo   make smoke           API smoke tests against localhost
	@echo.
	@echo   Code quality
	@echo   ----------------------------------------------------------------
	@echo   make lint            ruff + black check
	@echo   make format          ruff fix + black auto-format
	@echo   make env-check       Validate required environment variables
	@echo.
	@echo   Database
	@echo   ----------------------------------------------------------------
	@echo   make migrate         alembic upgrade head
	@echo   make rollback        alembic downgrade -1
	@echo   make seed            Populate development seed data
	@echo.
	@echo   Deployment + analytics
	@echo   ----------------------------------------------------------------
	@echo   make shell-backend        Open shell in backend container
	@echo   make shell-frontend       Open shell in frontend container
	@echo   make deploy               Rolling production deployment
	@echo   make analytics            Open Umami analytics dashboard
	@echo   make docker-up-analytics  Start Umami + its Postgres
	@echo   make monitoring-up        Start Prometheus + Grafana
	@echo   make prod-up              Full production stack
	@echo.

# =============================================================================
# venv — create isolated virtual environment
# =============================================================================
venv:
ifeq ($(OS),Windows_NT)
	$(PYTHON_SYS) -c "import os,sys; p='.venv\\Scripts\\python.exe'; exit(0) if os.path.exists(p) else [print('[venv] Creating .venv...'),os.system('python -m venv .venv'),print('[venv] Done.')]"
else
	@if [ ! -f .venv/bin/python ]; then \
	  echo "[venv] Creating .venv..."; \
	  python3 -m venv .venv; \
	  echo "[venv] Done."; \
	else \
	  echo "[venv] .venv already exists, skipping."; \
	fi
endif

# =============================================================================
# check-docker — preflight guard; all Docker-dependent targets depend on this
#
# Root-cause fix: GNU Make on Windows routes each recipe line through
# cmd.exe /c.  Multi-line @powershell ... \ continuations are broken by
# cmd.exe before PowerShell ever sees them.  The safe pattern is a single
# unbroken recipe line that invokes powershell.exe with -Command and a
# quoted one-liner, OR we use the cross-platform Python helper.
# We use Python here because it is always available and has no shell quoting
# hazards across cmd.exe, PowerShell, and bash.
# =============================================================================
check-docker:
	$(PYTHON) scripts/check_docker.py

# =============================================================================
# install — all dependencies into .venv
# =============================================================================
install: venv
	@echo [install] Upgrading pip inside .venv...
	$(PYTHON) -m pip install --upgrade pip
	@echo [install] Installing Python dependencies...
	$(PIP) install -r requirements.txt
	@echo [install] Installing Node.js packages...
ifeq ($(OS),Windows_NT)
	$(PYTHON) -c "import os; os.system('npm ci') if os.path.exists('package.json') else print('[install] No package.json, skipping npm.')"
else
	@if [ -f package.json ]; then npm ci; else echo "[install] No package.json, skipping npm."; fi
endif
	@echo [install] Done.

# =============================================================================
# dev — full development stack with hot reload
# =============================================================================
dev: check-docker
	@echo [dev] Starting development stack...
	@echo [dev]   Backend:   http://localhost:$(BACKEND_PORT)
	@echo [dev]   Analytics: http://localhost:$(ANALYTICS_PORT)
	@echo [dev]   API Docs:  http://localhost:$(BACKEND_PORT)/docs
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_ANALYTICS) up -d redis umami-db umami
	$(UVICORN) backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

# =============================================================================
# build — production Docker image
# =============================================================================
build: check-docker
	@echo [build] Building backend Docker image...
	docker build -f backend/Dockerfile -t $(FULL_IMAGE):$(IMAGE_TAG) -t $(FULL_IMAGE):latest --build-arg VCS_REF=$(IMAGE_TAG) .
	@echo [build] Backend image: $(FULL_IMAGE):$(IMAGE_TAG)
	@echo [build] Build complete.

# =============================================================================
# test targets
# =============================================================================
test:
	$(PYTEST) tests/ --ignore=tests/test_main_coverage.py --ignore=tests/test_live_factory.py --ignore=tests/test_live_marketing.py -v --tb=short --cov=backend --cov=agents --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-fail-under=$(COVERAGE_MIN)
	@echo [test] Coverage gate: >=$(COVERAGE_MIN)%

test-unit:
	$(PYTEST) tests/ --ignore=tests/test_main_coverage.py --ignore=tests/test_live_factory.py --ignore=tests/test_live_marketing.py --ignore=tests/test_commander.py --ignore=tests/test_company_generator.py --ignore=tests/test_deployment_service.py -v --tb=short --cov=backend --cov-report=term-missing -q

test-e2e:
	@echo [test-e2e] Running sovereign integration tests...
	$(PYTEST) tests_sovereign/test_db_integration.py tests_sovereign/test_factory_orchestration.py tests_sovereign/test_api.py tests_sovereign/test_workflow_service.py -v --tb=short

# =============================================================================
# lint / format
# =============================================================================
lint:
	@echo [lint] ruff check...
	$(PYTHON) -m ruff check .
	@echo [lint] black format check...
	$(PYTHON) -m black --check .
	@echo [lint] All lint checks passed.

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .
	$(PYTHON) -m black .

format-check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m black --check .

# =============================================================================
# Database
# =============================================================================
migrate:
	$(PYTHON) scripts/run_alembic.py upgrade head

rollback:
	$(PYTHON) scripts/run_alembic.py downgrade -1

seed:
	$(PYTHON) scripts/seed.py

db-migrate:
	$(PYTHON) scripts/run_alembic.py revision --autogenerate -m "$(MSG)"

db-upgrade:
	$(PYTHON) scripts/run_alembic.py upgrade head

db-downgrade:
	$(PYTHON) scripts/run_alembic.py downgrade -1

# =============================================================================
# Service lifecycle
# =============================================================================
launch: env-check check-docker
	@echo [launch] Running database migrations...
	$(MAKE) migrate
	@echo [launch] Seeding initial data...
	$(MAKE) seed
	@echo [launch] Starting services...
	$(PYTHON) scripts/launch_services.py
	@echo [launch] Running smoke tests...
	$(MAKE) smoke
	@echo.
	@echo [launch] All systems go. SwarmEnterprise v2 is live.
	@echo [launch]    API:       http://localhost:$(BACKEND_PORT)
	@echo [launch]    Dashboard: http://localhost:$(BACKEND_PORT)/dashboard/
	@echo [launch]    Analytics: http://localhost:$(ANALYTICS_PORT)

start: check-docker
	@echo [start] Starting production stack...
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE) --profile postgres --profile proxy --profile workers up -d --remove-orphans
	@echo [start] Services started. Waiting for readiness...
	$(PYTHON) scripts/wait_healthy.py $(BACKEND_PORT) 30
	$(MAKE) health

stop:
	@echo [stop] Stopping all services...
	$(PYTHON) scripts/stop_services.py

status:
	docker compose -f $(COMPOSE_FILE) ps

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# =============================================================================
# Health check (pure Python — no curl/bash required)
# =============================================================================
health:
	$(PYTHON) scripts/run_health_check.py $(BACKEND_PORT) $(ANALYTICS_PORT)

smoke:
	$(PYTHON) scripts/smoke_api.py --base-url http://localhost:$(BACKEND_PORT)

# =============================================================================
# Shells
# =============================================================================
shell-backend:
	docker compose -f $(COMPOSE_FILE) exec backend /bin/bash

shell-frontend:
	@echo [shell-frontend] Frontend is static HTML served by FastAPI/Caddy.
	$(MAKE) shell-backend

# =============================================================================
# Deploy
# =============================================================================
deploy: check-docker
	@echo [deploy] Pulling latest image...
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE) --profile postgres --profile proxy --profile workers pull
	@echo [deploy] Rolling deployment...
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE) --profile postgres --profile proxy --profile workers up -d --remove-orphans --pull always
	@echo [deploy] Running post-deploy health check...
	$(PYTHON) scripts/wait_healthy.py $(BACKEND_PORT) 30
	$(MAKE) health
	@echo [deploy] Deployment complete.

# =============================================================================
# Analytics
# =============================================================================
analytics:
	$(PYTHON) -c "import webbrowser; webbrowser.open('http://localhost:$(ANALYTICS_PORT)')"
	@echo [analytics] Opened http://localhost:$(ANALYTICS_PORT)

# =============================================================================
# Clean
# =============================================================================
clean:
	@echo [clean] Removing Docker containers and volumes...
	-docker compose -f $(COMPOSE_FILE) down --volumes --remove-orphans 2>nul
	-docker compose -f $(COMPOSE_ANALYTICS) down --volumes --remove-orphans 2>nul
	@echo [clean] Removing Python caches...
	$(PYTHON) scripts/clean_artifacts.py
	@echo [clean] Done.

# =============================================================================
# Env check
# =============================================================================
env-check:
	$(PYTHON) scripts/validate_env.py

# =============================================================================
# Docker Compose shortcuts
# =============================================================================
docker-build: check-docker
	docker compose -f $(COMPOSE_FILE) build

docker-up: check-docker
	docker compose -f $(COMPOSE_FILE) up -d

docker-up-wsl: check-docker
	docker compose -f $(COMPOSE_FILE) -f docker-compose.wsl-docker.yml up -d

docker-up-prod: check-docker
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE) --profile postgres --profile proxy --profile workers up -d

docker-up-analytics: check-docker
	@echo [analytics] Starting Umami analytics stack...
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_ANALYTICS) up -d umami-db umami
	$(PYTHON) scripts/wait_healthy.py $(ANALYTICS_PORT) 30 /api/heartbeat
	@echo [analytics] Umami dashboard: http://localhost:$(ANALYTICS_PORT)
	@echo [analytics] Default login:   admin / umami   -- change on first login!

docker-down:
	docker compose -f $(COMPOSE_FILE) down

docker-logs:
	docker compose -f $(COMPOSE_FILE) logs -f backend

monitoring-up: check-docker
	docker compose -f $(COMPOSE_FILE) -f deploy/docker/docker-compose.monitoring.yml up -d

monitoring-down:
	docker compose -f $(COMPOSE_FILE) -f deploy/docker/docker-compose.monitoring.yml down

prod-up: check-docker
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE) --profile ops --profile postgres --profile proxy --profile workers up -d

# =============================================================================
# Utilities
# =============================================================================
setup:
	$(PYTHON) scripts/setup_env.py

run:
	$(UVICORN) backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

verify:
	$(PYTHON) scripts/verify_secrets.py

heal:
	$(PYTHON) -c "from agents.ops.self_heal import run_heal_cycle; run_heal_cycle()"
