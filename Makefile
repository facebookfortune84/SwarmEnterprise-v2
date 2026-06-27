.PHONY: help setup install test run docker-build docker-up docker-down clean db-upgrade db-migrate db-downgrade monitoring-up monitoring-down prod-up

help:
	@echo "SwarmOS Development Commands"
	@echo "============================"
	@echo "  make setup          - Full local setup"
	@echo "  make install        - Install dependencies"
	@echo "  make test           - Run tests"
	@echo "  make run            - Run backend locally"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-up      - Start Docker containers"
	@echo "  make docker-down    - Stop Docker containers"
	@echo "  make clean          - Clean artifacts"
	@echo "  make monitoring-up  - Start monitoring stack alongside main services"
	@echo "  make monitoring-down - Stop monitoring stack"
	@echo "  make prod-up        - Start full production stack (all profiles + monitoring)"
	@echo ""
	@echo "Database Migration Commands"
	@echo "==========================="
	@echo "  make db-upgrade     - Apply all pending migrations (alembic upgrade head)"
	@echo "  make db-migrate MSG='description' - Autogenerate a new migration"
	@echo "  make db-downgrade   - Revert the last applied migration"

setup:
	bash setup.sh

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=agents --cov=backend

run:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

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

verify:
	python scripts/verify_secrets.py

heal:
	python -c "from agents.ops.self_heal import run_heal_cycle; run_heal_cycle()"

docker-logs:
	docker-compose logs -f backend

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/

db-upgrade:
	alembic upgrade head

db-migrate:
	alembic revision --autogenerate -m "$(MSG)"

db-downgrade:
	alembic downgrade -1

monitoring-up:
	docker compose -f docker-compose.yml -f deploy/docker/docker-compose.monitoring.yml up -d

monitoring-down:
	docker compose -f docker-compose.yml -f deploy/docker/docker-compose.monitoring.yml down

prod-up:
	docker compose -f docker-compose.yml -f deploy/docker/docker-compose.production-realms2riches.yml -f deploy/docker/docker-compose.monitoring.yml --profile ops --profile postgres --profile proxy up -d

lint:
	black .
	ruff check .

format:
	black .
	ruff check --fix .