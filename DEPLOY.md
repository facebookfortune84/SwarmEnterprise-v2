# SwarmOS Production Deployment

## Domain topology

| Host | Role |
|------|------|
| `realms2riches.com` | Main app + dashboard (`/dashboard`) |
| `corp.realms2riches.com` | Corporate static info only |
| `api.realms2riches.com` | FastAPI backend |
| `*.realms2riches.tech` | Per-company isolated boxes (Docker per tenant) |

## Physical architecture

```
[Laptop: ollama serve :11434]
        ↑ OLLAMA_URL (LAN IP or host.docker.internal)
[Hyper-V VM: Windows Server 2025]
        └── WSL2 Ubuntu + Docker
                ├── swarmOS-backend
                ├── swarmOS-redis
                ├── swarmOS-caddy (profiles: proxy)
                └── r2r-box-{slug} (tenant containers)
```

## OLLAMA_URL / networking (laptop ↔ WSL ↔ Docker)

1. On the **physical laptop**, run `ollama serve` and allow inbound TCP **11434** (Windows Firewall).
2. Find laptop LAN IP: `ipconfig` → e.g. `192.168.1.50`.
3. In **WSL2 on the Hyper-V VM**, `host.docker.internal` often points to the VM—not the laptop. Set in `.env`:

   ```bash
   LAPTOP_OLLAMA_HOST=192.168.1.50
   OLLAMA_URL=http://192.168.1.50:11434
   ```

4. Test from WSL: `curl http://192.168.1.50:11434/api/tags`
5. Test from a container: `docker run --rm curlimages/curl curl -s $OLLAMA_URL/api/tags`
6. **Docker Desktop on laptop** (not nested VM): use `docker-compose.local-laptop-ollama.yml` with default `host.docker.internal:11434`.
7. Optional **socat** on WSL if routing is broken: forward WSL localhost:11434 → laptop IP:11434.

Compose profiles:

```bash
# Laptop Docker Desktop + host Ollama
docker compose -f docker-compose.yml -f docker-compose.local-laptop-ollama.yml up -d

# WSL Docker on Hyper-V VM → laptop Ollama
docker compose -f docker-compose.yml -f docker-compose.wsl-docker.yml up -d

# Production stack + Caddy
docker compose -f docker-compose.yml -f docker-compose.production-realms2riches.yml --profile proxy --profile ops up -d
```

## Step-by-step: deploy to realms2riches.com

1. **DNS** — A records for `realms2riches.com`, `www`, `api`, `corp`, `realms2riches.tech`, `*.realms2riches.tech` → public IP of WSL/VM host.
2. **Server** — Windows Server 2025 VM with WSL2 Ubuntu; install Docker inside WSL.
3. **Clone & env** — `git clone` repo to `/srv/swarmenterprise`; copy `.env` from secrets (never commit).
4. **Secrets verify** — `python scripts/verify_secrets.py` or `scons verify`.
5. **Pull & up** — `docker compose -f docker-compose.yml -f docker-compose.wsl-docker.yml -f docker-compose.production-realms2riches.yml --profile proxy up -d`
6. **Caddy/SSL** — `deploy/Caddyfile` obtains certs via ACME when ports 80/443 are open.
7. **CI** — push to `main` triggers `.github/workflows/deploy.yml` (build GHCR image, SSH deploy).
8. **Tenant box** — POST `/api/tenants/register` then `/api/tenants/{id}/provision` from dashboard or API.

## Self-heal team

```bash
# One-shot heal
scons heal

# Continuous (production)
python -m agents.ops.scheduler
# Or Docker profile ops:
docker compose --profile ops up -d ops-heal
```

Logs: `output/ops_heal.log` (no secrets). Dashboard: **Run self-heal** → `POST /api/ops/heal`.

## Secret verification

```bash
scons verify
# or
python scripts/verify_secrets.py
```

Never prints secret values—only pass/fail/missing counts.

## Hyper-V VM automation (optional)

`scripts/hyperv/provision_vm.ps1` is a stub; full VM-per-tenant is documented for manual/Ops extension. **Working minimum:** Docker-per-tenant via `BoxDeployer`.

## Local Windows quick start

```powershell
.\scripts\setup_env.ps1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
scons
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# Dashboard: http://localhost:8000/dashboard/
```
