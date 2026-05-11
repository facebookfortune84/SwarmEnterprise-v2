.PHONY: help setup install test run docker-build docker-up docker-down clean

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
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f backend

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/

lint:
	black .
	ruff check .

format:
	black .
	ruff check --fix .