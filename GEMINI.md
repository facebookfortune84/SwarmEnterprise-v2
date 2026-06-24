# GEMINI.md

## Project Overview
SwarmEnterprise v2 is an autonomous digital factory platform designed to build, deploy, market, and maintain software companies with zero operational costs. It leverages a multi-agent system ("Swarm") to decompose complex missions into actionable tasks, utilizing AI-driven code generation, self-healing infrastructure, and proactive outreach.

- **Technology Stack**: Python (FastAPI), Docker, Hyper-V, Celery, Jinja2 (for templating).
- **Core Architecture**: Meta-Agent orchestrator (Commander) manages specialized agents (DevOps, Marketing, Ops, etc.).

## Building and Running
The project is managed via `launch_all.py` for the full factory environment and a `Makefile` for developer tasks.

### Key Commands:
*   **Full Launch**: `python3 launch_all.py`
*   **Local Backend**: `make run`
*   **Tests**: `make test`
*   **Install Deps**: `make install`
*   **Docker Management**: 
    *   Build: `make docker-build`
    *   Start: `make docker-up`
    *   Stop: `make docker-down`

## Development Conventions
*   **Style**: Adheres to `black` formatting and `ruff` linting. Run `make lint` or `make format` to enforce.
*   **Testing**: Unit tests are located in `tests/` and `tests_sovereign/`. Use `make test` to execute them.
*   **Architecture**: Logic is strictly separated into `agents/` (agent-specific logic), `backend/` (FastAPI core, services), and `scripts/` (administrative/operational tasks).
*   **Secrets**: Always verify secrets using `make verify` (`scripts/verify_secrets.py`) before deployment.

## Useful Resources
*   **Documentation**: Located in `docs/` and `assets/sops/`.
*   **Operational Logs**: Check the `logs/` directory for system diagnostics.
