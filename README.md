# SwarmEnterprise v2 🚀

**The 100% Autonomous Digital Factory Platform**  
*RWV Techsolutions LLC · [Contact](mailto:robertdemottojr50@gmail.com)*

[![License: FOSS](https://img.shields.io/badge/License-FOSS-green)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Docker 24.x](https://img.shields.io/badge/Docker-24.x-brightblue)](https://www.docker.com/get-started)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success)](./docs/LAUNCH_CHECKLIST.md)

---

## What is SwarmEnterprise v2?

SwarmEnterprise is an **autonomous AI-powered platform** that generates, deploys, and operates full-stack applications with zero human intervention. It combines:

- **16 Specialized AI Agents** — from DevOps to Lead Discovery
- **Autonomous Factory Engine** — generates code, deploys to cloud or Docker
- **Self-Healing Infrastructure** — monitors and auto-recovers from failures
- **Dual Delivery Modes** — Downloadable ZIP bundles or hosted VMs
- **Built-in Marketing** — proactive lead discovery and outreach
- **100% FOSS** — no vendor lock-in, fully open-source

**In 5 minutes, you can generate a complete SaaS company.**

---

## 📖 Table of Contents

- [Quick Start](#quick-start) — 5 minutes to running
- [Features](#features) — What you get
- [Architecture](#architecture) — How it works
- [Installation](#installation) — Step-by-step setup
- [Usage](#usage) — Running the platform
- [Deployment](#deployment) — Production launch
- [Development](#development) — Contributing
- [Legal](#legal) — License & policies
- [Support](#support) — Getting help

---

## Quick Start

### Prerequisites

| Tool | Version | Link |
|------|---------|------|
| **Docker** | 24.x+ | [Download](https://www.docker.com/get-started) |
| **Docker Compose** | v2 | Bundled with Docker Desktop |
| **Python** | 3.11+ | [Download](https://www.python.org/downloads/) |
| **Git** | 2.x+ | [Download](https://git-scm.com/) |

### 1. Clone & Configure ✅

```bash
# Clone the repository
git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git
cd swarmenterprise-v2

# Copy environment template
cp .env.example .env

# Generate secure secrets (JWT keys, encryption keys, etc.)
python scripts/generate_secrets.py
```

**✅ Checkpoint:** You should see:
```
Generated JWT_SECRET_KEY: 64-char hex string
Generated SECRET_KEY: 64-char hex string
Generated ENCRYPTION_KEY: base64-encoded string
```

### 2. Edit Configuration ✅

```bash
# Open .env in your editor
# Windows (PowerShell): notepad .env
# macOS/Linux:         nano .env
# Or use VS Code:      code .env

# Minimum required settings:
# POSTGRES_PASSWORD=  (any strong password)
# ADMIN_PASSWORD=     (for admin user)
# OLLAMA_URL=         (local: http://host.docker.internal:11434 OR remote)
```

**Optional but recommended:**
- `STRIPE_API_KEY` — for payment processing
- `SMTP_SERVER` / `SMTP_USER` / `SMTP_PASS` — for sending emails
- `SENTRY_DSN` — for error tracking

**✅ Checkpoint:** Your `.env` file is saved without syntax errors.

### 3. Launch Everything ✅

```bash
# Single command to validate, build, migrate, seed, and start
make launch
```

**What this does automatically:**
1. Validates all environment variables
2. Creates/migrates database schema
3. Seeds initial data (admin user, demo data)
4. Builds Docker images
5. Starts all services
6. Runs health checks (waits for readiness)
7. Runs smoke tests (verifies API endpoints)

**⏱️ Estimated time:** 3–5 minutes on first run (includes Docker image downloads)

### 4. Verify It's Working ✅

Open your browser to the URLs below. All should return status `200 OK`:

| Service | URL | What to expect |
|---------|-----|-----------------|
| **API Health** | http://localhost:8000/health | `{"status": "ONLINE"}` |
| **Swagger Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics (technical) |
| **Frontend Dashboard** | http://localhost:8000/dashboard | Web UI (if frontend is built) |
| **Flower (Workers)** | http://localhost:5555 | Celery task monitor |

**✅ Checkpoint:** All URLs return 200 status. You are ready to use the platform.

---

## Features

### 🤖 16 AI Agents

Each agent is specialized for a specific business function:

| Agent | Purpose | Examples |
|-------|---------|----------|
| **Swarm Commander** | Decompose high-level missions into tasks | "Create a SaaS for managing invoices" → tickets |
| **Factory Engine** | Generate code from templates + LLM | Creates full-stack apps in minutes |
| **Marketing Lead Discovery** | Find prospective customers proactively | Scrapes LinkedIn, crawls websites, builds lists |
| **Outreach Worker** | Autonomous cold email campaigns | Sends personalized emails, tracks opens/clicks |
| **DevOps Deployment** | Provision VMs, deploy code, manage infrastructure | Creates Hyper-V VMs or Docker containers |
| **Self-Healing Ops** | Monitor and auto-fix infrastructure issues | Detects failures, restarts services, alerts team |
| **Billing & Payments** | Process Stripe charges, manage subscriptions | Creates invoices, tracks usage, handles disputes |
| **[+ 8 more]** | Auth, notifications, support, analytics, … | See `/agents` directory |

### 🏭 Autonomous Factory

**Describe a product in natural language. Get a fully-built company in minutes.**

**Input:**
```
"I want a SaaS platform that manages remote teams. Include timesheets, approval workflows, 
and integrations with Slack. Deploy to the cloud and auto-scale."
```

**Output:**
- ✅ Full-stack web application (React frontend, FastAPI backend)
- ✅ Database schema (PostgreSQL + migrations)
- ✅ Docker images (multi-stage builds, optimized for production)
- ✅ Kubernetes manifests OR Hyper-V VM provisioning
- ✅ GitHub repository with CI/CD workflows
- ✅ Landing page + pricing calculator
- ✅ Legal documents (Terms, Privacy Policy, ToS)
- ✅ Deployment script (one-click launch)

**Available as:**
- Downloadable ZIP bundle (self-hosted)
- Managed VM on `.tech` domain (fully hosted by us)

### 🛡️ Self-Healing Infrastructure

SwarmEnterprise monitors itself and auto-recovers:

- **Health Checks:** Every 30 seconds, verify all services are responding
- **Auto-Restart:** If a service crashes, it restarts automatically
- **Alert Notifications:** Team gets notified of failures before users notice
- **Log Aggregation:** All logs centralized in structured JSON format
- **Graceful Degradation:** If one component fails, others continue working

### 📊 Proactive Marketing

Generate leads WITHOUT a starting list:

1. **Discovery:** Agent scrapes LinkedIn, Twitter, industry blogs, company directories
2. **Targeting:** Filters by industry, company size, job title, recent hiring
3. **Enrichment:** Adds email addresses, phone numbers, decision-maker names
4. **Outreach:** Sends personalized cold emails with A/B testing
5. **Tracking:** Monitors opens, clicks, replies; auto-follows up

**All autonomous.** No manual work after configuration.

### 💰 Payment Processing

Integrated Stripe support:

- Accept credit cards, ACH, Apple Pay, Google Pay
- Manage subscriptions (monthly, annual, usage-based)
- Invoice generation and delivery
- Webhook handling (charge succeeded, subscription updated, etc.)
- Automatic retry on failed charges
- Dispute handling

### 🔐 Security

- JWT-based stateless authentication (no sessions)
- OAuth 2.0 support (GitHub, Google, etc.)
- Rate limiting (120 requests/minute by default, configurable)
- CORS protection (configurable allowed origins)
- SQL injection protection (parameterized queries via SQLAlchemy ORM)
- XSS protection (FastAPI sanitizes responses)
- HTTPS mandatory in production (auto-provisioned via Let's Encrypt)
- Secrets encrypted at rest (Fernet symmetric encryption)
- Audit logging (all API calls logged with user + timestamp)

---

## Architecture

```
                        ┌──────────────────────────────────────────┐
                        │           Internet / CDN                 │
                        └────────────────────┬─────────────────────┘
                                             │ HTTPS
                        ┌────────────────────▼─────────────────────┐
                        │     Caddy (reverse proxy + TLS)          │
                        │      Auto-renew Let's Encrypt            │
                        └────────────────────┬─────────────────────┘
                                             │ HTTP
             ┌───────────────────────────────▼──────────────────────────────┐
             │                  Frontend Network                            │
             │  ┌──────────────────────────────────────────────────────┐   │
             │  │           FastAPI Backend (:8000)                    │   │
             │  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │   │
             │  │  │ Auth Router │  │ Middleware   │  │  /metrics  │  │   │
             │  │  │ API Router  │  │  Prometheus  │  │  /health   │  │   │
             │  │  │ Agents API  │  │  CorrID      │  │  /docs     │  │   │
             │  └──────────────────────────────────────────────────────┘   │
             └─────────────────────────┬────────────────────────────────────┘
                                       │
             ┌─────────────────────────▼────────────────────────────────────┐
             │             Backend Network (internal only)                  │
             │                                                               │
             │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐ │
             │  │ PostgreSQL   │   │  Redis 7     │   │ Celery Workers   │ │
             │  │  (5432)      │   │  (6379)      │   │ + Beat + Flower  │ │
             │  │  Primary DB  │   │  Message Br. │   │  Task Processor  │ │
             │  └──────────────┘   └──────────────┘   └──────────────────┘ │
             └───────────────────────────────────────────────────────────────┘

  AI Agent Layer
  ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
  │   Swarm      │   Factory    │  Marketing   │  Deployment  │  Self-Heal   │
  │  Commander   │   Engine     │ Lead Discovery│   Service    │   Ops        │
  └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Key Components:**

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **FastAPI Backend** | REST API, business logic | Python 3.11, FastAPI 0.104 |
| **PostgreSQL** | Relational data store | PostgreSQL 16 |
| **Redis** | Message broker, caching | Redis 7 |
| **Celery Workers** | Async task processing | Celery + Beat scheduler |
| **Caddy** | Reverse proxy, HTTPS | Caddy 2 (auto Let's Encrypt) |
| **AI Agents** | Core intelligence | CrewAI, LangChain, Ollama/LLMs |

---

## Installation

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # includes testing tools

# Setup local env
cp .env.example .env
python scripts/generate_secrets.py
# Edit .env with local values (can leave most as defaults)

# Run migrations locally
python scripts/run_alembic.py upgrade head

# Seed data locally
python scripts/seed.py

# Start backend (with hot reload)
make run
# OR
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker (Recommended for Production)

```bash
# See Quick Start section above
make launch
```

### Environment Variables

**Required for production:**
- `JWT_SECRET_KEY` — JWT signing key (64-char hex)
- `SECRET_KEY` — Session/cookie key (64-char hex)
- `POSTGRES_PASSWORD` — Database password
- `ADMIN_PASSWORD` — Admin user initial password

**Optional but recommended:**
- `STRIPE_API_KEY` — For payment processing
- `SMTP_SERVER`, `SMTP_USER`, `SMTP_PASS` — For email
- `SENTRY_DSN` — For error tracking

**See [.env.example](./.env.example) for all 100+ variables.**

---

## Usage

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/health` | Service health (DB, Redis, Ollama status) |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Swagger UI (interactive API docs) |
| `POST` | `/auth/register` | Create new user account |
| `POST` | `/auth/login` | User login (returns JWT) |
| `GET` | `/auth/me` | Get current user info |
| `POST` | `/companies` | Create a new company |
| `GET` | `/companies/{id}` | Get company details |
| `POST` | `/deployments` | Deploy a company to cloud/Docker |
| `GET` | `/deployments/{id}` | Check deployment status |
| ... | ... | See `/docs` for full list |

**Example: Create a company**

```bash
curl -X POST http://localhost:8000/companies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "TechCorp Inc",
    "industry": "SaaS",
    "description": "A platform for managing remote teams",
    "target_market": "US Enterprise"
  }'

# Response:
# {
#   "id": "uuid",
#   "name": "TechCorp Inc",
#   "status": "created",
#   "created_at": "2026-06-29T10:00:00Z"
# }
```

### Command-Line Interface (Make)

```bash
make help              # List all available commands
make launch           # Full startup (validate → build → migrate → seed → start → test)
make stop             # Graceful shutdown
make status           # Show running containers
make logs             # Tail all logs
make test             # Run full test suite with coverage
make lint             # Code quality checks
make migrate          # Run database migrations
make seed             # Populate initial data
make health           # Health check all services
make smoke            # API smoke tests
```

### Web UI

1. Open http://localhost:8000/dashboard
2. Login with credentials you set during `make seed`
3. Create a new company using the form
4. Watch as agents generate code, design database, create deployment manifests
5. Deploy to cloud or Docker

---

## Deployment

### Local Testing

```bash
# Start full dev stack with hot reload
make dev

# Backend auto-reloads on file changes
# Frontend is static HTML (no hot reload)
```

### Production Deployment

**See [docs/LAUNCH_RUNBOOK.md](./docs/LAUNCH_RUNBOOK.md) for step-by-step.**

Quick summary:

1. **Provision cloud VM** (IONOS, AWS, Azure, DigitalOcean)
2. **SSH in and clone repo**
3. **Copy .env.example → .env, fill with production values**
4. **Run: `make launch`**
5. **Wait 3–5 minutes, verify services are healthy**
6. **Point DNS to VM IP, configure firewall (ports 80, 443)**
7. **Monitor logs for errors**

**See also:**
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Detailed deployment guide
- [LAUNCH_CHECKLIST.md](./docs/LAUNCH_CHECKLIST.md) — Pre-launch verification
- [LAUNCH_RUNBOOK.md](./docs/LAUNCH_RUNBOOK.md) — Step-by-step deployment procedure

---

## Development

### Project Structure

```
swarmenterprise-v2/
├── backend/                 # FastAPI application
│   ├── main.py             # App entry point
│   ├── config.py           # Configuration (env vars)
│   ├── api/                # API routers
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── companies.py    # Company CRUD
│   │   ├── deployments.py  # Deployment management
│   │   └── ...
│   ├── db/                 # Database layer
│   │   ├── models.py       # SQLAlchemy ORM models
│   │   ├── session.py      # DB connection management
│   │   └── ...
│   ├── services/           # Business logic
│   ├── tasks/              # Celery async tasks
│   └── ...
├── agents/                 # AI agents (CrewAI)
│   ├── commander/          # Swarm Commander agent
│   ├── factory/            # Factory Engine agent
│   ├── marketing/          # Lead discovery agent
│   ├── outreach/           # Cold email agent
│   ├── devops/             # Deployment agent
│   └── ...
├── frontend/               # Static HTML/CSS/JS
│   └── public/             # Served by FastAPI
├── deploy/                 # Docker & Kubernetes configs
│   ├── Dockerfile          # Backend container
│   ├── Caddyfile           # Reverse proxy config
│   └── ...
├── tests/                  # Test suite
│   ├── test_*.py          # Unit/integration tests
│   └── ...
├── scripts/                # Utility scripts
│   ├── seed.py            # Populate DB with demo data
│   ├── generate_secrets.py # Generate cryptographic secrets
│   └── ...
├── alembic/                # Database migrations
├── docker-compose.yml      # Local development
├── docker-compose.prod.yml # Production hardening overlay
├── Makefile                # Build automation
├── pyproject.toml          # Python project metadata
└── README.md               # This file
```

### Testing

```bash
# Run all tests with coverage report
make test

# Run unit tests only (faster)
make test-unit

# Run integration tests (requires running services)
make test-e2e

# Check code quality
make lint

# Auto-format code
make format
```

### Contributing

1. **Fork** the repository on GitHub
2. **Create a feature branch**: `git checkout -b feature/my-agent`
3. **Write tests** for your changes
4. **Commit** with clear messages: `git commit -m "Add new AI agent for X"`
5. **Push** to your fork: `git push origin feature/my-agent`
6. **Open a Pull Request** with description of changes

**Before submitting:**
- [ ] All tests pass: `make test`
- [ ] Code is formatted: `make format`
- [ ] No lint errors: `make lint`
- [ ] Coverage ≥ 90%: `make test | grep "coverage"`

**See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.**

---

## Legal

### License

This project is **100% FOSS (Free and Open Source Software)** under the MIT License. See [LICENSE](./LICENSE) for details.

You are free to:
- ✅ Use for commercial projects
- ✅ Modify and fork
- ✅ Contribute improvements
- ✅ Self-host and deploy anywhere

### Legal Documents

- [Privacy Policy](./frontend/public/privacy-policy.html) — How we handle user data
- [Terms of Service](./frontend/public/terms.html) — Platform usage terms
- [SECURITY.md](./SECURITY.md) — Security policy and reporting vulnerabilities
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — Community standards

---

## Support

### Documentation

- 📖 [Full Deployment Guide](./DEPLOYMENT.md)
- 🚀 [Launch Runbook](./docs/LAUNCH_RUNBOOK.md)
- ✅ [Launch Checklist](./docs/LAUNCH_CHECKLIST.md)
- 🏗️ [Architecture Overview](./docs/architecture/ARCHITECTURE.md)
- 🤝 [Contributing Guide](./CONTRIBUTING.md)

### Getting Help

| Channel | Use For |
|---------|---------|
| **GitHub Issues** | Bug reports, feature requests |
| **GitHub Discussions** | Q&A, architecture discussions |
| **Email** | [robertdemottojr50@gmail.com](mailto:robertdemottojr50@gmail.com) |
| **API Docs** | http://localhost:8000/docs (Swagger UI) |

### Common Issues

| Issue | Solution |
|-------|----------|
| "Connection refused" | Is Docker running? Try `docker ps` |
| "Health check timeout" | Database not ready. Check `docker compose logs postgres` |
| "Import error" | Install deps: `pip install -r requirements.txt` |
| "Port already in use" | Change `BACKEND_PORT` in `.env` or kill the process |
| "SSL certificate error" | Wait for DNS propagation; check firewall allows 80/443 |

See [DEPLOYMENT.md § 7 Troubleshooting](./DEPLOYMENT.md#7-troubleshooting) for more.

---

## Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Backend API** | ✅ Production Ready | FastAPI, fully tested, 92% coverage |
| **Database Layer** | ✅ Production Ready | PostgreSQL migrations, connection pooling |
| **AI Agents** | ✅ Production Ready | 16 agents, CrewAI integration, error handling |
| **Frontend UI** | ✅ Basic Ready | Static HTML, can be extended with React/Vue |
| **Docker Setup** | ✅ Production Ready | Multi-stage builds, security hardening, resource limits |
| **Monitoring** | ✅ Production Ready | Prometheus metrics, health checks, Sentry integration |
| **Documentation** | ✅ Complete | Full deployment guides, API docs, troubleshooting |

---

## Statistics

- **Lines of Code:** 15,000+
- **API Endpoints:** 50+
- **Database Tables:** 35+
- **Test Coverage:** 92%
- **AI Agents:** 16
- **License:** MIT (100% FOSS)
- **Python Version:** 3.11+
- **Docker Image Size:** ~800MB (optimized multi-stage build)

---

## Roadmap

### v2.0 (Current) — Autonomous Factory

- ✅ Core AI agents (16 implemented)
- ✅ Code generation engine
- ✅ Deployment automation
- ✅ Payment processing (Stripe)
- ✅ Email outreach
- ✅ Self-healing infrastructure
- ✅ Full test coverage (92%)

### v2.1 (Q3 2026) — Multi-Tenant SaaS

- [ ] Tenant isolation & data segregation
- [ ] Role-based access control (RBAC)
- [ ] Advanced analytics & usage tracking
- [ ] Custom branding & whitelabeling
- [ ] API rate limiting per tenant

### v2.2 (Q4 2026) — Agent Marketplace

- [ ] Community agent sharing
- [ ] Agent versioning & rollback
- [ ] Rating & reviews system
- [ ] Revenue sharing model

---

## Credits

**Built by:** RWV Techsolutions LLC  
**Contact:** [robertdemottojr50@gmail.com](mailto:robertdemottojr50@gmail.com)  
**Location:** Elkins, WV, USA

**Powered by:**
- FastAPI · CrewAI · LangChain · PostgreSQL · Redis · Celery · Docker · Caddy

---

## Quick Links

- 🌐 [Website](https://realms2riches.com)
- 💼 [LinkedIn](https://linkedin.com/in/rdmottojr)
- 🐙 [GitHub](https://github.com/rwv-techsolutions)
- 📧 [Email](mailto:robertdemottojr50@gmail.com)

---

**SwarmEnterprise v2 — Ship complete companies. In minutes. 🚀**
