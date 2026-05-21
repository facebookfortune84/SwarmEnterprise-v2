# SwarmOS Deploy & Local Runbook

## Zero-touch local setup (Windows)

```powershell
# From repo root
.\scripts\setup_env.ps1          # creates .env from .env.example if missing
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
scons                            # deps + lint + pip-audit + tests + API smoke
```

## Zero-touch local setup (Linux / WSL / macOS)

```bash
bash setup.sh                    # venv, deps, copies .env when missing
scons
```

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `SWARM_OUTPUT_DIR` | Generated apps, invoices, bundles | `<repo>/output` |
| `SWARM_REPO_ROOT` | Repo root for codegen scripts | auto-detected |
| `SWARM_DB_URL` | SQLAlchemy URL for tickets DB | `sqlite:///<repo>/pg_data/swarm_tickets.db` |
| `OLLAMA_URL` | Local LLM gateway | `http://host.docker.internal:11434` |
| `STRIPE_API_KEY` / `STRIPE_WEBHOOK_SECRET` | Payments webhooks | placeholders for dev |
| `SMTP_*` | Outreach email | mocked when `SMTP_PASS` empty |

Copy `.env.example` via `scripts/setup_env.ps1` (Windows) or `setup.sh` (Unix). Never commit `.env`.

## Run API

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# Health: GET http://localhost:8000/health
```

## Docker

```bash
docker compose up -d
```

Mounts the repo at `/mnt/c/SwarmEnterprise_v2` inside the container; set `SWARM_OUTPUT_DIR=/mnt/c/SwarmEnterprise_v2/output` in `.env` when using Docker.

## CI parity

GitHub Actions (`.github/workflows/ci.yml`): `pip-audit`, `pytest`, `black --check`, `ruff check`.

Local equivalent: `scons` (default target).
