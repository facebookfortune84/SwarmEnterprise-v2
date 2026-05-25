# Copilot Instructions for SwarmEnterprise-v2 (SwarmOS)

This file collects repository-specific instructions for Copilot-based sessions: how to build, test, lint, the big-picture architecture, and repository conventions that matter across files.

---

## 1) Build, test, and lint commands

- Local setup (venv / dev):
  - Run setup script: bash setup.sh
  - Install Python deps: make install  (runs `pip install -r requirements.txt`)

- Run backend locally (development):
  - make run
  - Or: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

- Docker / containerized dev:
  - Build images: make docker-build  (uses docker-compose)
  - Start containers: make docker-up  (maps repo into container at /mnt/c/SwarmEnterprise_v2)
  - Stop containers: make docker-down

- Tests:
  - Full test suite: make test   (runs `pytest tests/ -v --cov=agents --cov=backend`)
  - Run a single test file: pytest tests/unit/backend/test_routes.py -q
  - Run a single test function: pytest tests/unit/backend/test_routes.py::test_health_check -q
  - Pytest config is in pyproject.toml (testpaths = ["tests"], pattern: test_*.py)

- Lint & format:
  - Lint: make lint  (runs `black .` then `ruff check .`)
  - Auto-format: make format (black + ruff check --fix)
  - Black settings: line-length = 100 (pyproject.toml)

- Misc scripts:
  - Test network bridge: python test_network_bridge.py
  - Helper scripts live in `scripts/` (asset generation, fixes, ingestion)

---

## 2) High-level architecture (big picture)

- Purpose: SwarmOS is an AI-driven "digital factory" that accepts build requests and dispatches an AI Swarm to assemble projects.

- Major components:
  - backend/: FastAPI application providing API routes and webhooks. Entrypoint: `backend.main:app`.
    - `/health` endpoint used for healthchecks and tests.
    - `/api` router exposes core endpoints (e.g., POST /api/build) which enqueue background work using FastAPI BackgroundTasks.
  - backend/core/: contains the `swarm_factory` that drives the production cycles (long-running agent orchestration).
  - agents/: AI agent implementations (managers, workers, config). These contain the business logic for autonomous behaviors.
  - assets/: prompts, SOPs, tool manifests, and other data-driven content used by agents and tests.
  - docker-compose.yml: defines a `backend` service that mounts the repo into the container at `/mnt/c/SwarmEnterprise_v2` and expects several environment variables (OLLAMA, embedding model, Stripe, SMTP, etc.). Uses healthcheck against /health.
  - Persistence & vectors: repo depends on SQLAlchemy + aiosqlite and Chroma (chromadb) for embedding/vector storage.

- Runtime pattern:
  - API receives a request -> handler schedules `swarm_factory.run_production_cycle` as a background task -> agents package executes logic (possibly calling local LLMs via Ollama or remote APIs) -> artifacts are persisted into the mounted output directory.
  - Long-running tasks are expected to run outside the request lifecycle (BackgroundTasks / background workers).

- Dev hot-reload pattern: Uvicorn with --reload is used for local development; containers mount source for in-container reload.

---

## 3) Key conventions and repository-specific patterns

- API & routing:
  - Core API routes are prefixed with `/api` (see backend/api/routes.py).
  - Webhooks and additional routers are included in backend.main via `app.include_router(...)`.

- Background work:
  - Trigger long-running AI work via FastAPI `BackgroundTasks` to avoid blocking requests. The primary entrypoint is `swarm_factory.run_production_cycle`.

- Filesystem mounts and paths:
  - Docker and code assume the repository is mounted at `/mnt/c/SwarmEnterprise_v2` inside containers. main.py creates `/mnt/c/SwarmEnterprise_v2/output/src` at startup—Copilot sessions that run or test code in-container should be aware of this path mapping.

- Tests & TestClient:
  - tests/conftest.py provides a pytest fixture `client()` that yields FastAPI TestClient(app). Use that fixture for unit tests that exercise HTTP endpoints.
  - Tests follow pytest naming conventions (test_*.py) and are configured via pyproject.toml.

- Formatting / linting policy:
  - Black line-length is set to 100; ruff is used for linting. Use the provided Makefile targets to run both.

- Dependency & Python version:
  - Requires Python >= 3.11 (pyproject.toml). dev extras in pyproject include pinned versions for pytest, black, ruff, mypy.

- AI / LLM integrations:
  - Project expects local or remote LLM endpoints. docker-compose environment variables include OLLAMA_URL and model settings. Many agent prompts live under assets/prompts/ and assets/tools/ are used to configure tool sets.

- Assets and SOPs:
  - assets/sops/ contains operational runbooks (useful context for agent behavior); assets/prompts/ contains canonical prompt templates—these are authoritative for agent prompts and should be consulted when adjusting agent behavior.

---

## 4) Files to check for extra context (quick pointers)

- README.md (quick start & local steps)
- Makefile (shortcuts for build/test/run/lint)
- pyproject.toml (dependencies, pytest config, Black/Ruff settings)
- docker-compose.yml and backend/Dockerfile (container behavior, mounts, env vars)
- backend/core/factory.py (the production cycle driver) — consult before changing orchestration logic
- agents/ (AI code; many integrations and configuration points)

---

If this file exists already in .github/, prefer patching it rather than replacing it wholesale. This document focuses only on repo-specific commands, architecture, and conventions useful to Copilot sessions.
