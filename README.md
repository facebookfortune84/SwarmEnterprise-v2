# SwarmEnterprise v2 🚀
**The 100% Autonomous Digital Factory Platform**  
*RWV Techsolutions LLC — robertdemottojr50@gmail.com*

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git
cd swarmenterprise-v2

# 2. Configure
cp .env.example .env
python scripts/generate_secrets.py   # generates JWT_SECRET_KEY, SECRET_KEY, etc.
$EDITOR .env                         # fill in DATABASE_URL / POSTGRES_PASSWORD

# 3. Launch everything
make launch
```

`make launch` handles everything automatically:
validate env → run migrations → seed data → start services → health check → smoke test.

After launch:

| Service | URL |
|---------|-----|
| **API** | `http://localhost:8000` |
| **Swagger Docs** | `http://localhost:8000/docs` |
| **Health** | `http://localhost:8000/health` |
| **Metrics** | `http://localhost:8000/metrics` |
| **Flower** | `http://localhost:5555` |

To stop: `make stop`

---

## 🌟 Key Features

- **16 Operational AI Agents:** Specialized workers for everything from DevOps to Lead Discovery.
- **Autonomous Factory:** One-click generation of full-stack "Company in a Box" applications.
- **Dual Delivery Modes:** Choose between a downloadable ZIP bundle or automated VM hosting on the `.tech` domain.
- **Self-Healing Infrastructure:** Autonomous health monitoring and recovery (Hyper-V & Docker).
- **Proactive Marketing:** Autonomous lead discovery and outreach even without a starting list.
- **Legal Suite:** Pre-configured Privacy Policy and Terms of Service.

---

## 🏗️ Architecture

```
                        ┌──────────────────────────────────────────┐
                        │               Internet / CDN              │
                        └────────────────────┬─────────────────────┘
                                             │ HTTPS
                        ┌────────────────────▼─────────────────────┐
                        │           Caddy  (reverse proxy)          │
                        │         Auto TLS via Let's Encrypt         │
                        └────────────────────┬─────────────────────┘
                                             │ HTTP
             ┌───────────────────────────────▼──────────────────────────────┐
             │                  frontend network                            │
             │  ┌──────────────────────────────────────────────────────┐   │
             │  │              FastAPI Backend  (:8000)                 │   │
             │  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │   │
             │  │  │ API Routers │  │  Middleware   │  │  /metrics  │  │   │
             │  │  │ (auth, pay, │  │  CorrID +     │  │  /health   │  │   │
             │  │  │  agents…)   │  │  Prometheus   │  │  /docs     │  │   │
             │  └──────────────────────────────────────────────────────┘   │
             └─────────────────────────┬────────────────────────────────────┘
                                       │
             ┌─────────────────────────▼────────────────────────────────────┐
             │                   backend network (internal)                 │
             │                                                               │
             │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
             │  │  PostgreSQL  │   │    Redis 7    │   │  Celery Worker   │ │
             │  │  (port 5432) │   │  (port 6379)  │   │  + Beat + Flower │ │
             │  │  Named vol   │   │  AOF persist  │   │  (port 5555)     │ │
             │  └──────────────┘   └──────────────┘   └──────────────────┘ │
             └───────────────────────────────────────────────────────────────┘

  Agent Layer
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │  Swarm   │ │ Factory  │ │Marketing │ │Outreach  │ │  DevOps  │ │  Ops     │
  │Commander │ │ Engine   │ │Lead Disc.│ │  Worker  │ │Deployment│ │Self-Heal │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

- **Meta-Agent (Swarm Commander):** Decomposes high-level missions into actionable tickets.
- **Factory Engine:** Uses Jinja2 templates and LLM code generation.
- **Deployment Service:** Orchestrates Hyper-V VMs and Docker containers.
- **Monetization Layer:** Integrated Stripe webhooks for payments and hosting billing.

---

## 🛠️ Make Targets

```
make launch       Validate → build → migrate → seed → start → health → smoke
make stop         Graceful shutdown of all services
make status       Show running containers and health
make logs         Tail logs from all services
make health       Poll /health endpoint
make smoke        Run API smoke tests
make lint         ruff check --fix + ruff format
make test         pytest with coverage
make migrate      alembic upgrade head
make rollback     alembic downgrade -1
make seed         Seed initial DB data
make env-check    Validate required environment variables
make clean        Remove containers, volumes, build artefacts
```

Run `make help` for the full list.

---

## 📂 Project Structure

```
swarmenterprise-v2/
├── backend/           FastAPI app, DB engines, API routers
├── agents/            AI agents (marketing, outreach, ops, …)
├── assets/            SOPs, prompts, agent tools
├── deploy/            Docker + Caddy + monitoring configs
├── docs/              Architecture and phase documentation
├── frontend/          Static dashboard and marketing site
├── output/            Generated company code (persistent)
├── scripts/           Operational scripts (seed, smoke, secrets, …)
├── start.sh           Full launch script
├── stop.sh            Graceful shutdown
├── docker-compose.yml Base service definitions
├── docker-compose.prod.yml  Production hardening overlay
├── Makefile           All build and ops commands
├── .env.example       Environment variable template
├── DEPLOYMENT.md      Full deployment guide
└── CHANGELOG.md       Change history
```

---

## 📜 Documentation

- 📦 **[Deployment Guide](DEPLOYMENT.md)** — Quick start, env var reference, production setup, scaling, monitoring, troubleshooting
- 📋 **[Changelog](CHANGELOG.md)** — Full history of changes
- 🏛️ **[Architecture](docs/architecture/ARCHITECTURE.md)** — System design
- 🖥️ **[Self-Hosted Setup](docs/architecture/SELF_HOSTED_ARCHITECTURE.md)** — On-prem guide
- 🎯 **[Lead Generation SOP](assets/sops/LEAD_EXTRACTION.md)** — Agent lead extraction

---

## ⚖️ Legal

- [Privacy Policy](frontend/public/privacy-policy.html)
- [Terms of Service](frontend/public/terms.html)

---

**Status:** Production Ready ✅  
**Cost:** $0/month operational  
**Built with:** ❤️ and Swarm Intelligence by RWV Techsolutions LLC
