# SwarmEnterprise v2 — Makefile
# RWV Techsolutions LLC · robertdemottojr50@gmail.com
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help \
        launch stop status logs \
        seed lint test migrate rollback health smoke clean env-check \
        setup install run \
        docker-build docker-up docker-up-wsl docker-up-prod docker-down docker-logs \
        verify heal \
        db-upgrade db-migrate db-downgrade \
        monitoring-up monitoring-down prod-up format

# ─────────────────────────────────────────────────────────────────────────────
# Default target
# ─────────────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  SwarmEnterprise v2 — Build & Operations"
	@echo "  RWV Techsolutions LLC"
	@echo "  ════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Launch / Lifecycle"
	@echo "  ────────────────────────────────────────────────────────"
	@echo "  make launch       Validate → build → migrate → seed → start → health"
	@echo "  make stop         Graceful shutdown of all services"
	@echo "  make status       Show running containers and their health"
	@echo "  make logs         Tail logs from all services"
	@echo "  make health       Poll /health endpoint on running backend"
	@echo "  make smoke        Run API smoke tests against localhost"
	@echo "  make clean        Remove containers, volumes, and build artifacts"
	@echo ""
	@echo "  Database"
	@echo "  ────────────────────────────────────────────────────────"
	@echo "  make migrate      alembic upgrade head"
	@echo "  make rollback     alembic downgrade -1"
	@echo "  make seed         Run scripts/seed.py"
	@echo "  make db-migrate MSG='...'  Autogenerate a new migration"
	@echo ""
	@echo "  Code Quality"
	@echo "  ────────────────────────────────────────────────────────"
	@echo "  make lint         ruff check --fix + ruff format"
	@echo "  make test         pytest with coverage"
	@echo "  make env-check    Validate all required environment variables"
	@echo ""
	@echo "  Legacy / Docker shortcuts"
	@echo "  ────────────────────────────────────────────────────────"
	@echo "  make setup        Full local setup (runs setup.sh)"
	@echo "  make install      pip install -r requirements.txt"
	@echo "  make run          uvicorn backend.main:app --reload"
	@echo "  make docker-build docker-compose build"
	@echo "  make docker-up    Start local-laptop-ollama stack"
	@echo "  make docker-down  docker compose down"
	@echo "  make monitoring-up / monitoring-down"
	@echo "  make prod-up      Full production stack"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# NEW: Launch & Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

## Single command: validate + build + migrate + seed + start + health check + smoke test
launch: env-check
	@echo "[launch] Running database migrations …"
	$(MAKE) migrate
	@echo "[launch] Seeding initial data …"
	$(MAKE) seed
	@echo "[launch] Starting services …"
	bash start.sh
	@echo "[launch] Running smoke tests …"
	$(MAKE) smoke
	@echo ""
	@echo "[launch] All systems go. SwarmEnterprise v2 is live."

## Graceful shutdown of all services
stop:
	bash stop.sh

## Show status of all services and their health
status:
	docker compose ps

## Tail logs from all services (Ctrl-C to exit)
logs:
	docker compose logs -f

## Run database seed script
seed:
	python scripts/seed.py

## Run ruff check --fix and ruff format
lint:
	ruff check --fix .
	ruff format .

## Run pytest with coverage
test:
	pytest tests/ -v --cov=agents --cov=backend

## Run alembic upgrade head
migrate:
	alembic upgrade head

## Run alembic downgrade -1
rollback:
	alembic downgrade -1

## Check health of all running services
health:
	@PORT=$${BACKEND_PORT:-8000}; \
	URL="http://localhost:$${PORT}/health"; \
	echo "Polling $${URL} …"; \
	if curl -sf "$${URL}"; then \
	  echo ""; echo "[OK] Backend is healthy."; \
	else \
	  echo "[FAIL] Backend health check failed. Is it running?"; exit 1; \
	fi

## Run API smoke tests against localhost
smoke:
	python scripts/smoke_api.py --base-url http://localhost:$${BACKEND_PORT:-8000}

## Validate all required environment variables
env-check:
	python scripts/validate_env.py

## Remove containers, volumes, and build artifacts
clean:
	docker compose down --volumes --remove-orphans 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/

# ─────────────────────────────────────────────────────────────────────────────
# EXISTING: Local development
# ─────────────────────────────────────────────────────────────────────────────

setup:
	bash setup.sh

install:
	pip install -r requirements.txt

run:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# ─────────────────────────────────────────────────────────────────────────────
# EXISTING: Docker shortcuts
# ─────────────────────────────────────────────────────────────────────────────

docker-build:
	docker-compose build

docker-up:
	docker compose -f docker-compose.yml -f docker-compose.local-laptop-ollama.yml up -d

docker-up-wsl:
	docker compose -f docker-compose.yml -f docker-compose.wsl-docker.yml up -d

docker-up-prod:
	docker compose -f docker-compose.yml -f docker-compose.wsl-docker.yml -f docker-compose.production-realms2riches.yml --profile proxy up -d

docker-down:
	docker compose down

docker-logs:
	docker-compose logs -f backend

# ─────────────────────────────────────────────────────────────────────────────
# EXISTING: Utilities
# ─────────────────────────────────────────────────────────────────────────────

verify:
	python scripts/verify_secrets.py

heal:
	python -c "from agents.ops.self_heal import run_heal_cycle; run_heal_cycle()"

# ─────────────────────────────────────────────────────────────────────────────
# EXISTING: Database migrations
# ─────────────────────────────────────────────────────────────────────────────

db-upgrade:
	alembic upgrade head

db-migrate:
	alembic revision --autogenerate -m "$(MSG)"

db-downgrade:
	alembic downgrade -1

# ─────────────────────────────────────────────────────────────────────────────
# EXISTING: Monitoring
# ─────────────────────────────────────────────────────────────────────────────

monitoring-up:
	docker compose -f docker-compose.yml -f deploy/docker/docker-compose.monitoring.yml up -d

monitoring-down:
	docker compose -f docker-compose.yml -f deploy/docker/docker-compose.monitoring.yml down

prod-up:
	docker compose -f docker-compose.yml -f deploy/docker/docker-compose.production-realms2riches.yml -f deploy/docker/docker-compose.monitoring.yml --profile ops --profile postgres --profile proxy up -d

# ─────────────────────────────────────────────────────────────────────────────
# EXISTING: Code quality (legacy aliases kept)
# ─────────────────────────────────────────────────────────────────────────────

format:
	black .
	ruff check --fix .
