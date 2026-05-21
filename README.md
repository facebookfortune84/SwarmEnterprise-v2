# SwarmOS v2.0 - Autonomous Digital Factory

## Quick Start (zero manual steps beyond secrets)

### Windows (PowerShell)

```powershell
.\scripts\setup_env.ps1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
scons
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Linux / WSL / macOS

```bash
bash setup.sh
scons
make run
```

See [DEPLOY.md](DEPLOY.md) for environment variables, Docker, and CI parity.

## Verify

- `scons` — install deps, ruff, black, pip-audit, pytest, API smoke (`/health`)
- `pytest tests -q` — unit and integration tests
- `GET /health` — returns `{"status":"ONLINE",...}`

## Project layout

- `backend/` — FastAPI app, webhooks, billing, connectors
- `agents/` — CrewAI board, outreach, workers
- `scripts/` — codegen (`generate_*.py`), `setup_env.ps1`, smoke test
- `tests/` — pytest suite wired in SConstruct
