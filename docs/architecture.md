# Architecture — SwarmEnterprise v2

**Version**: 2.0.0  
**Audience**: Engineers onboarding to the project, senior contributors, and
DevOps engineers responsible for deployment and operations.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Component Diagram](#high-level-component-diagram)
3. [Backend Layer](#backend-layer)
4. [Data Layer](#data-layer)
5. [Async Task Layer](#async-task-layer)
6. [Authentication and Authorization Flow](#authentication-and-authorization-flow)
7. [AI Agent Layer](#ai-agent-layer)
8. [External Integrations](#external-integrations)
9. [Directory Structure Reference](#directory-structure-reference)
10. [Key Design Decisions](#key-design-decisions)

---

## System Overview

SwarmEnterprise v2 is an **autonomous digital factory platform** that combines
a multi-tenant SaaS backend with an AI agent swarm. The system provides:

- **REST API** (FastAPI) — tenant management, ticketing, workflow automation,
  notifications, billing, and authentication
- **Autonomous Agents** — 16 specialized AI workers (marketing, DevOps, code
  review, documentation, etc.) coordinated by a central commander
- **Background Task Queue** (Celery + Redis) — asynchronous ticket processing,
  SLA monitoring, email delivery, workflow step execution
- **Multi-Tenant Isolation** — each customer tenant gets a provisioned
  container or VM with its own stack
- **Self-Healing Infrastructure** — continuous health monitoring with automatic
  recovery via the `agents/ops` layer

The system is deployed on Docker Compose for local/staging and scales to
production Postgres + Redis with Celery workers.

---

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT TIER                                │
│  Browser (frontend/public/)   ·   API consumers   ·   Webhooks     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS / HTTP
┌───────────────────────────────▼─────────────────────────────────────┐
│                        REVERSE PROXY                                │
│                    Caddy 2 (TLS termination)                        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                        API GATEWAY LAYER                            │
│  FastAPI application  ·  backend/main.py                            │
│                                                                     │
│  Middleware stack (outermost → innermost):                          │
│    RateLimitMiddleware  →  CorrelationIDMiddleware  →               │
│    PrometheusMetricsMiddleware  →  CORSMiddleware  →  Router        │
└──────┬──────────────────────────────────────────┬───────────────────┘
       │ SQLAlchemy (sync)                         │ Celery tasks
┌──────▼──────────────────┐        ┌──────────────▼─────────────────┐
│      DATA LAYER         │        │       ASYNC TASK LAYER          │
│                         │        │                                 │
│  PostgreSQL 16          │        │  Redis 7 (broker + results)     │
│  ├── users              │        │  ├── Celery worker(s)           │
│  ├── tickets            │        │  │   ├── ticket_tasks           │
│  ├── workflows          │        │  │   ├── notification_tasks      │
│  ├── notifications      │        │  │   └── workflow_tasks          │
│  ├── api_keys           │        │  └── Celery beat (scheduler)    │
│  ├── company_tenants    │        │      ├── check_sla_breaches/30m │
│  ├── deployments        │        │      └── escalate_overdue/1h    │
│  └── …(12 tables)       │        │                                 │
│                         │        │  Flower (monitoring UI :5555)   │
│  Alembic migrations     │        └─────────────────────────────────┘
│  alembic/versions/      │
└─────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────────┐
│                        AI AGENT LAYER                               │
│                                                                     │
│  agents/managers/commander.py  ←→  agents/managers/board.py        │
│                                                                     │
│  Specialized agents:                                                │
│  ├── marketing/   (lead_discovery, content_creator)                │
│  ├── devops/      (ci_cd_manager, deployment_agent, …)             │
│  ├── code_review/ (code_reviewer, security_auditor, …)             │
│  ├── outreach/    (email_engine, worker)                           │
│  ├── ticketing/   (backlog_manager, ticket_prioritizer)            │
│  ├── ops/         (monitor, scheduler, self_heal)                  │
│  └── self_healing/(circuit_breaker, health_monitor, auto_recovery) │
│                                                                     │
│  LLM Backend: Ollama (local) / Groq / Anthropic / Google           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Backend Layer

### Entry Point

[`backend/main.py`](../backend/main.py) initialises the FastAPI application,
registers all middleware, mounts all routers, and defines the `lifespan`
context manager (startup/shutdown). Configuration is validated at import time
via [`backend/config.py`](../backend/config.py).

### Middleware Stack

Applied in order (outermost to innermost):

| Middleware | Purpose |
|-----------|---------|
| `RateLimitMiddleware` | Per-IP request rate limiting (default 120 req/min) |
| `CorrelationIDMiddleware` | Attaches `X-Request-ID` to every request/response |
| Prometheus `@app.middleware("http")` | Records per-route latency and status counts |
| `CORSMiddleware` | Origin validation against `CORS_ORIGINS` env var |

### Routers

| Module | Prefix | Description |
|--------|--------|-------------|
| `api/auth.py` | `/api/auth` | Registration, login, logout, token refresh |
| `api/users.py` | `/api/users` | User CRUD and admin management |
| `api/tickets.py` | `/api/tickets` | Ticket lifecycle management |
| `api/notifications.py` | `/api/notifications` | User notification inbox |
| `api/workflows.py` | `/api/workflows` | Multi-step workflow engine |
| `api/payments.py` | `/api/payments` | Stripe billing integration |
| `api/webhooks.py` | `/api/webhooks` | Stripe and external webhooks |
| `api/admin.py` | `/api/admin` | Platform-level admin operations |
| `api/deployments.py` | `/api/deployments` | Tenant deployment management |
| `api/companies.py` | `/api/companies` | Company/tenant generation |
| `api/gdpr.py` | `/api/gdpr` | GDPR data export and erasure |
| `api/outreach.py` | `/api/outreach` | Autonomous outreach control |
| `api/voice.py` | `/api/voice` | ElevenLabs voice synthesis |
| `api/ws.py` | `/ws` | WebSocket real-time events |
| `api/leads.py` | `/api/leads` | Lead management |
| `api/usage.py` | `/api/usage` | Usage metering |
| `api/tenants.py` | `/api/tenants` | Multi-tenancy management |
| `api/ops.py` | `/api/ops` | Operations and self-healing |

### Configuration

[`backend/config.py`](../backend/config.py) uses `pydantic-settings`
`BaseSettings` sub-classes grouped by subsystem:

```
Settings
├── DatabaseSettings   (DATABASE_URL)
├── RedisSettings      (REDIS_HOST, REDIS_PORT, REDIS_URL)
├── StripeSettings     (STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET)
├── SmtpSettings       (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
├── JwtSettings        (JWT_SECRET_KEY, *_EXPIRE_*)
├── LlmSettings        (OLLAMA_URL, OLLAMA_MODEL, EMBEDDING_MODEL)
└── DeploymentSettings (SSH_HOST, CLOUDFLARE_*, TECH_DOMAIN)
```

A startup validator on `JwtSettings.secret_key` raises `ValueError` if the
default placeholder is used in any non-local `DEPLOY_PROFILE`.

---

## Data Layer

### ORM

All database access uses **SQLAlchemy 2.0 ORM** (synchronous sessions). The
`get_db` FastAPI dependency in [`backend/db/session.py`](../backend/db/session.py)
is the **only** correct way to obtain a session inside request handlers:

```python
# Correct
async def my_route(db: Session = Depends(get_db)):
    ...

# Never do this inside a FastAPI route handler
db = SessionLocal()   # ❌
```

### Database Models

All ORM models are defined in [`backend/db/models.py`](../backend/db/models.py)
and registered with `Base.metadata`.

| Model | Table | Key Fields |
|-------|-------|-----------|
| `User` | `users` | id, email, password_hash, role, is_active |
| `APIKey` | `api_keys` | key, user_id, scope, expires_at |
| `CompanyTenant` | `company_tenants` | slug, subdomain, status |
| `Deployment` | `deployments` | tenant_id, status, strategy |
| `Ticket` | `tickets` | title, status, priority, sla_hours |
| `TicketComment` | `ticket_comments` | ticket_id, user_id, content |
| `TicketHistory` | `ticket_history` | ticket_id, action, old_value, new_value |
| `Notification` | `notifications` | user_id, type, is_read |
| `MessageThread` | `message_threads` | subject, participants_json |
| `Message` | `messages` | thread_id, sender_id, content |
| `Workflow` | `workflows` | name, status, current_step, steps_json |
| `WorkflowStep` | `workflow_steps` | workflow_id, step_type, status |
| `Project` | `projects` | stripe_session, customer_email |
| `Lead` | `leads` | email, status |
| `UsageEvent` | `usage_events` | project_id, event_type |
| `ProcessedEvent` | `processed_events` | event_id (idempotency) |

### Migration History

| Revision | Description |
|----------|-------------|
| `0001` | Initial 9-table schema |
| `0002` | Phase 2 — 7 new tables + 10 ticket columns |

---

## Async Task Layer

### Celery Application

[`backend/celery_app.py`](../backend/celery_app.py) defines the Celery
application with:

- **Broker**: Redis (or `memory://` in test mode)
- **Queues**: `default`, `high_priority`, `low_priority`, `tickets`,
  `notifications`, `dlq` (dead-letter)
- **Beat schedule**: SLA breach check (30 min), overdue ticket escalation (hourly)

### Task Modules

| Module | Tasks |
|--------|-------|
| `tasks/ticket_tasks.py` | `process_ticket`, `check_sla_breaches`, `escalate_overdue_tickets` |
| `tasks/notification_tasks.py` | `send_notification`, `send_email_notification`, `broadcast_event` |
| `tasks/workflow_tasks.py` | `execute_workflow_step`, `handle_step_failure`, `advance_workflow` |

All tasks open their own `SessionLocal()` session (Celery workers run outside
the request context), handle exceptions with retry logic, and close the session
in a `finally` block.

### Event Bus

[`backend/services/event_bus.py`](../backend/services/event_bus.py) provides a
lightweight in-process pub/sub bus. Handlers can be sync or async. Built-in
subscriptions:

| Event | Handler | Action |
|-------|---------|--------|
| `task.failed` | `_on_task_failed` | Creates incident ticket |
| `workflow.completed` | `_on_workflow_completed` | Notifies admins |
| `workflow.failed` | `_on_workflow_failed` | Notifies admins |

---

## Authentication and Authorization Flow

```
1. Client sends POST /api/auth/login {email, password}
         │
2. UserService.authenticate_user() — bcrypt.checkpw()
         │
3. create_access_token() + create_refresh_token()
   Both are HS256 JWTs signed with JWT_SECRET_KEY.
   Access token carries: sub (user_id), email, role, type="access", exp
         │
4. Client stores tokens; sends Authorization: Bearer <access_token>
         │
5. get_current_user() dependency:
   a. is_token_revoked(token) → Redis EXISTS "revoked:<token>"
   b. decode_token(token) → jwt.decode() → returns payload or None
   c. Checks payload.type == "access"
         │
6. get_current_active_user() dependency:
   Queries User table to verify is_active=True
         │
7. get_current_admin_user() dependency:
   Checks payload.role in {"admin", "superadmin"}
         │
8. On logout: revoke_token(token) → Redis SETEX "revoked:<token>" ttl "1"
         │
9. On token expiry: client calls POST /api/auth/refresh {refresh_token}
   refresh_access_token() verifies type=="refresh", not revoked, returns new access token
```

### Role Hierarchy

```
superadmin  ← all permissions
  └── admin ← manage users, delete tickets, access admin endpoints
        └── user ← standard access to own resources
```

---

## AI Agent Layer

The agent layer is organised as independent specialist agents coordinated by a
commander:

```
agents/managers/commander.py
├── Reads the task queue
├── Selects the appropriate specialist agent
└── Dispatches tasks via agents/managers/board.py

Specialists:
  agents/marketing/      → lead discovery, content creation
  agents/devops/         → CI/CD, deployment, infrastructure, security scanning
  agents/code_review/    → code quality, security audit, style checks
  agents/documentation/  → API docs, changelog, doc generation
  agents/outreach/       → email engine, worker queue
  agents/ticketing/      → backlog management, prioritization, Linear integration
  agents/ops/            → monitoring, scheduling, self-healing
  agents/self_healing/   → circuit breaker, health monitor, auto recovery
```

LLM calls are routed through [`backend/llm/ollama_client.py`](../backend/llm/ollama_client.py)
(local Ollama) with fallback to cloud providers via `GROQ_API_KEY`,
`ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY`.

---

## External Integrations

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Stripe** | Payment processing, subscriptions | `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` |
| **Ollama** | Local LLM inference | `OLLAMA_URL`, `OLLAMA_MODEL` |
| **Groq** | Cloud LLM fallback | `GROQ_API_KEY` |
| **Anthropic** | Cloud LLM fallback | `ANTHROPIC_API_KEY` |
| **Google AI** | Cloud LLM / embeddings | `GOOGLE_API_KEY` |
| **ElevenLabs** | Text-to-speech | `ELEVENLABS_API_KEY` |
| **HubSpot** | CRM integration | `HUBSPOT_ACCESS_TOKEN` |
| **Cloudflare** | Tunnel / DNS automation | `CLOUDFLARE_TUNNEL_TOKEN` |
| **Sentry** | Error tracking | `SENTRY_DSN` |
| **OpenTelemetry** | Distributed tracing | `OTEL_OTLP_ENDPOINT` |
| **Prometheus** | Metrics scraping | `/metrics` endpoint |
| **Linear** | Project management | `LINEAR_API_KEY` |
| **GitHub** | Container registry, CI/CD | `GITHUB_TOKEN`, `GHCR_*` |

---

## Directory Structure Reference

```
swarmenterprise-v2/
├── backend/                   FastAPI application
│   ├── api/                   Route handlers (one file per domain)
│   ├── auth/                  JWT handler, middleware, user service, permissions
│   ├── celery_app.py          Celery configuration and beat schedule
│   ├── config.py              Pydantic settings (env var validation)
│   ├── core/                  Factory, deployment service, tenant logic
│   ├── db/
│   │   ├── base.py            SQLAlchemy declarative base
│   │   ├── models.py          All 16 ORM models
│   │   ├── session.py         Engine, SessionLocal, get_db dependency
│   │   └── ticket_history.py  Audit trail helpers
│   ├── llm/                   Ollama client
│   ├── main.py                FastAPI app, middleware, lifespan
│   ├── metrics.py             Prometheus counters/histograms
│   ├── orchestration/         VM provisioner, box deployer
│   ├── queue.py               Redis queue utilities
│   ├── services/              Business logic services
│   │   ├── ticket_service.py
│   │   ├── notification_service.py
│   │   ├── workflow_service.py
│   │   ├── event_bus.py
│   │   └── …
│   ├── storage/               S3 / file manager
│   ├── tasks/                 Celery task modules
│   └── telemetry.py           OTEL initialisation
│
├── agents/                    AI agent swarm
│   ├── managers/              Commander, board
│   ├── marketing/             Lead discovery, content
│   ├── devops/                CI/CD, deployment, security
│   ├── code_review/           Quality, security auditing
│   ├── documentation/         Doc generation, changelog
│   ├── outreach/              Email engine and worker
│   ├── ticketing/             Backlog, prioritization
│   ├── ops/                   Monitor, scheduler, self-heal
│   └── self_healing/          Circuit breaker, recovery
│
├── alembic/                   Database migration scripts
│   ├── env.py                 Alembic environment (imports all models)
│   └── versions/              Migration files (0001, 0002, …)
│
├── tests/                     pytest test suite
│   ├── conftest.py            Shared fixtures
│   ├── fixtures/              Test data factories
│   ├── unit/                  Unit tests by subsystem
│   └── utils/                 Test helpers
│
├── tests_sovereign/           Integration test suite
│   ├── test_api.py            Notifications + Workflows API
│   ├── test_workflow_service.py  WorkflowService unit tests
│   ├── test_db_integration.py
│   └── test_factory_orchestration.py
│
├── deploy/                    Deployment configs
│   ├── Caddyfile              Reverse proxy config
│   └── docker/                Environment-specific compose overrides
│
├── scripts/                   Operational scripts
│   ├── generate_secrets.py    Cryptographically strong secret generation
│   ├── validate_env.py        Pre-flight env var check
│   ├── smoke_api.py           API smoke test runner
│   ├── seed.py                Database seed data
│   └── backup_postgres.sh     Postgres backup
│
├── docs/                      Documentation
│   ├── api.md                 REST API reference
│   ├── deployment.md          Deployment guide
│   ├── architecture.md        This file
│   └── guides/                Operational guides
│
├── frontend/public/           Static frontend assets
├── docker-compose.yml         Base compose file
├── docker-compose.prod.yml    Production overrides
├── backend/Dockerfile         Multi-stage production image
├── docker-entrypoint.sh       Container startup script
├── alembic.ini                Alembic configuration
├── pyproject.toml             Python package and tool config
├── requirements.txt           Production dependencies
├── requirements-dev.txt       Development dependencies
├── .env.example               Environment variable template
├── CONTRIBUTING.md            Contributor guide
├── SECURITY.md                Security policy
├── CODE_OF_CONDUCT.md         Community standards
├── CHANGELOG.md               Release history
└── VERSION                    Current semantic version
```

---

## Key Design Decisions

### 1. Synchronous SQLAlchemy over asyncpg

The application uses synchronous `Session` rather than `AsyncSession`. This was
chosen for simplicity and compatibility with the Celery task layer, which always
runs synchronously. The `get_db` FastAPI dependency uses a standard generator
(`yield db`) wrapped in `try/finally` to guarantee session cleanup.

### 2. lifespan over on_event

FastAPI's `@app.on_event("startup")` is deprecated. The codebase uses the
`@contextlib.asynccontextmanager` lifespan pattern introduced in FastAPI 0.93+,
which gives correct control over startup and shutdown ordering.

### 3. JWT revocation via Redis blacklist

JWTs are stateless by design, but logout requires immediate revocation. Rather
than short-expiry tokens with frequent refresh, the system uses a Redis
blacklist (`SETEX "revoked:<token>" ttl "1"`). On Redis failure the system
fails-open (treats token as valid) with an error log — a deliberate trade-off
to avoid Redis outage causing total authentication failure.

### 4. Pydantic v2 throughout

All models use Pydantic v2 patterns: `model_dump()` instead of `.dict()`,
`model_validate()` instead of `.from_orm()`, and `model_config = ConfigDict(from_attributes=True)`
instead of `class Config`. The `pydantic-settings` package handles environment
variable binding.

### 5. Event bus for loose coupling

Services communicate via the in-process `EventBus` rather than calling each
other directly. This keeps services independently testable and allows adding
new reactions (e.g. a new notification type) without modifying existing code.

### 6. Celery in-memory transport for tests

Setting `TEST_MODE=true` redirects Celery to use `memory://` broker and
`cache+memory://` backend, eliminating the need for a running Redis instance
in CI and unit tests.

---

*Made with IBM Bob*
