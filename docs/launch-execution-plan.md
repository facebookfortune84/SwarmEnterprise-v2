# SwarmEnterprise v2 — Launch Execution Plan

**Goal:** Complete every unchecked item in `docs/PRE_LAUNCH_CHECKLIST.md` so the platform reaches full production readiness, and ensure the entire agent workforce has structured access to the `assets/` folder.

**Orchestration Note:** This plan is designed to be executed in **Orchestrator mode** after review. Each sub-task is self-contained so multiple sub-agents can work in parallel. Every sub-task begins by reading this file for full context.

---

## Assets Workforce Access Policy

The `assets/` folder is the **single source of truth** for all agent prompts, SOPs, and tool definitions. Each sub-task implementation must:
1. Reference relevant SOPs from `assets/sops/` (e.g. `TEC_001_DB_SCHEMA_MIGRATION.md` for migrations).
2. Reference relevant tool definitions from `assets/tools/` when calling LLM-powered agents.
3. Reference relevant prompts from `assets/prompts/` when initializing personas.
4. Log completion artifacts to the Lineage Registry per `assets/sops/GOV_007_LINEAGE_SIGNATURE.md`.
5. Any new agent, script, or service created must import/load from the registry at `assets/registry.json`.

A new `assets/ASSETS_README.md` (created in Sub-Task 1) will serve as the canonical guide for all workforce members to discover and use assets.

---

## Sub-Tasks Overview

| # | Name | Domain | Status |
|---|------|--------|--------|
| 1 | Assets Workforce Access Guide | Governance | [ ] pending |
| 2 | Database Migration Framework | Infrastructure | [ ] pending |
| 3 | Environment & Secrets Configuration | Infrastructure | [ ] pending |
| 4 | Docker Compose Production Stack Completion | Infrastructure | [ ] pending |
| 5 | Alembic Migration — Initial Schema | Infrastructure | [ ] pending |
| 6 | Prometheus Alerting Rules | Monitoring | [ ] pending |
| 7 | Grafana Dashboard Definitions | Monitoring | [ ] pending |
| 8 | Alertmanager Configuration | Monitoring | [ ] pending |
| 9 | Monitoring Docker Compose Integration | Monitoring | [ ] pending |
| 10 | Automated Database Backup Script | Backup & Recovery | [ ] pending |
| 11 | Disaster Recovery Runbook | Backup & Recovery | [ ] pending |
| 12 | Security Hardening — Firewall & Infrastructure | Security | [ ] pending |
| 13 | CDN & Rate Limiting Configuration | Performance | [ ] pending |
| 14 | Horizontal Scaling & Load Balancer Config | Scalability | [ ] pending |
| 15 | GDPR Compliance & Legal Pages | Compliance | [ ] pending |
| 16 | Staging Smoke Test Script | Deployment | [ ] pending |
| 17 | Checklist Completion & Final Verdict Update | Governance | [ ] pending |

---

## Sub-Task 1 — Assets Workforce Access Guide

**Intent:** Create a single canonical `assets/ASSETS_README.md` that describes the purpose of every folder, how to locate the right SOP/prompt/tool, and how agents should reference these assets in their workflows. This ensures every sub-agent spawned in orchestrator mode can orient itself quickly.

**Expected Outcomes:**
- `assets/ASSETS_README.md` exists with a categorized index of all SOPs, prompts, and tool files.
- Each entry includes: filename, one-sentence description, and when to use it.
- A usage protocol section explains the 5-step asset consumption pattern.
- `assets/registry.json` is updated to include SOP and tool entries (not just prompts).

**Todo List:**
1. Read the full `assets/` directory listing (already done — see directory tree in this plan).
2. Read a sample of 3 SOPs to understand their common structure (GOV_001, TEC_001, SEC_001).
3. Write `assets/ASSETS_README.md` with:
   - Introduction and folder structure
   - Full index table: SOPs (by category), Prompts (by model/use), Tools (by target LLM)
   - Asset Consumption Protocol (5 steps aligned with SOP Mandatory Procedures)
   - Quick Reference: which SOP covers which scenario
4. Update `assets/registry.json` to add `"sops"` and `"tools"` arrays alongside the existing `"prompts"` array.

**Relevant Context:**
- Asset directory: `assets/` (prompts/, sops/, tools/, registry.json)
- SOP structure: Initialize Persona → RAG fetch → Execute → Log artifacts → Mark RESOLVED
- All 47 SOPs follow this 5-step pattern
- Tool files: `assets/tools/Agent Tools.json`, `claude-4-sonnet-tools.json`, `gpt-5-tools.json`, `phase_mode_tools.json`, `plan_mode_tools.json`
- Registry: `assets/registry.json` (currently indexes only prompts)

**Status:** [ ] pending

---

## Sub-Task 2 — Database Migration Framework (Alembic)

**Intent:** The codebase uses SQLAlchemy ORM models but has no migration framework. Before any production deployment, we need Alembic set up so schema changes are tracked, reversible, and reproducible. This directly resolves the "Database migrations ready" checklist item.

**Expected Outcomes:**
- `alembic.ini` at project root.
- `alembic/` directory with `env.py` configured to read `DATABASE_URL` from the environment.
- `alembic/versions/` directory with the initial migration that creates all 9 tables from `backend/db/models.py`.
- `Makefile` updated with `make db-migrate` and `make db-upgrade` targets.
- `docs/guides/DEPLOYMENT_GUIDE.md` updated with migration step.

**Todo List:**
1. Read `backend/db/models.py` to capture all 9 model definitions.
2. Read `backend/db/base.py` or equivalent to find the SQLAlchemy `Base`.
3. Install/confirm `alembic` is in `requirements.txt`.
4. Run `alembic init alembic` equivalent — create `alembic.ini` and `alembic/env.py`.
5. Configure `alembic/env.py` to import `Base.metadata` from `backend.db.models` and read `DATABASE_URL`.
6. Generate initial migration file under `alembic/versions/` that creates all tables.
7. Add `make db-upgrade` to `Makefile`.
8. Reference: `assets/sops/TEC_001_DB_SCHEMA_MIGRATION.md` for procedure alignment.

**Relevant Context:**
- Models: `backend/db/models.py` (9 models: User, APIKey, CompanyTenant, Deployment, Ticket, Project, Lead, UsageEvent, ProcessedEvent)
- ORM base likely in `backend/db/base.py` or defined inline
- `DATABASE_URL` env var is blank in `.env.example` — must be set at deploy time
- `pyproject.toml` and `requirements.txt` manage Python deps

**Status:** [ ] pending

---

## Sub-Task 3 — Environment & Secrets Configuration

**Intent:** Produce a complete, documented environment configuration guide and a secrets management procedure so that any operator can provision a production `.env` from scratch, covering all 142 variables with validation.

**Expected Outcomes:**
- `scripts/setup_env.py` — a Python script that validates the `.env` file and reports which critical vars are missing/blank, grouped by service (DB, Redis, Stripe, SMTP, JWT, Hyper-V).
- `scripts/generate_secrets.py` — generates strong random values for `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and any other secrets that should never be manually typed.
- `docs/guides/SECRETS_MANAGEMENT.md` — step-by-step guide: which variables are required vs optional, where to get each value (Stripe dashboard, SMTP provider, etc.), and how to rotate secrets (reference `assets/sops/SEC_001_SECRET_PROTECTION.md` and `TEC_006_API_KEY_ROTATION.md`).
- `.env.example` updated with inline comments on every blank variable explaining what it should contain.

**Todo List:**
1. Read full `.env.example` to catalog all variables and their current inline comments.
2. Read `assets/sops/SEC_001_SECRET_PROTECTION.md` and `assets/sops/TEC_006_API_KEY_ROTATION.md`.
3. Write `scripts/validate_env.py`: reads `.env`, checks each required var, prints ✅/❌ per group.
4. Write `scripts/generate_secrets.py`: uses `secrets` module to print recommended values for JWT_SECRET_KEY, POSTGRES_PASSWORD, SMTP passwords.
5. Write `docs/guides/SECRETS_MANAGEMENT.md` with per-service setup instructions.
6. Annotate `.env.example` with clear inline comments for every blank variable.

**Relevant Context:**
- `.env.example` lines 1–142 (all env vars)
- Stripe vars: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`
- SMTP vars: `SMTP_USER`, `SMTP_PASS`, `SMTP_SERVER`, `SMTP_PORT`
- Redis: `REDIS_URL=redis://redis:6379/0`
- Database: `DATABASE_URL` (blank), `POSTGRES_PASSWORD` (blank)
- JWT: `JWT_SECRET_KEY` not yet in `.env.example` — must be added
- Existing script: `scripts/verify_secrets.py`, `scripts/scan_env.ps1`
- SEC SOP reference: `assets/sops/SEC_001_SECRET_PROTECTION.md`

**Status:** [ ] pending

---

## Sub-Task 4 — Docker Compose Production Stack Completion

**Intent:** The base `docker-compose.yml` has profiles for postgres, workers, ops, proxy — but monitoring services (Prometheus, Grafana, Loki, Promtail, node-exporter, cAdvisor) are not in any compose file. Wire up the full production monitoring stack and update the production compose override.

**Expected Outcomes:**
- `deploy/docker/docker-compose.monitoring.yml` — new overlay that adds: Prometheus, Grafana, Loki, Promtail, node-exporter, cAdvisor services with correct volumes and network membership.
- `deploy/docker/docker-compose.production-realms2riches.yml` updated to reference the monitoring overlay.
- Grafana is pre-configured to auto-load Prometheus and Loki datasources via provisioning files.
- `Makefile` updated with `make up-prod` target that brings up all profiles + monitoring.
- All monitoring services join the `swarmnet` Docker network.

**Todo List:**
1. Read `deploy/docker/docker-compose.production-realms2riches.yml` to understand current production overrides.
2. Read `monitoring/prometheus.yml`, `monitoring/loki-config.yml`, `monitoring/promtail-config.yml`.
3. Create `monitoring/grafana/provisioning/datasources/datasources.yml` — declares Prometheus (port 9090) and Loki (port 3100) datasources.
4. Create `deploy/docker/docker-compose.monitoring.yml` with services: prometheus, grafana, loki, promtail, node-exporter, cadvisor. Mount existing monitoring configs. Expose Grafana on port 3000.
5. Update `deploy/docker/docker-compose.production-realms2riches.yml` to import monitoring overlay (or document the compose command).
6. Update root `Makefile` with `make monitoring-up` and `make prod-up` targets.
7. Reference: `assets/sops/TEC_010_TELEMETRY_DASHBOARD.md` and `TEC_005_DOCKER_CONTAINER_UPKEEP.md`.

**Relevant Context:**
- Existing monitoring configs: `monitoring/prometheus.yml`, `monitoring/loki-config.yml`, `monitoring/promtail-config.yml`
- `monitoring/alerts/` directory does NOT exist yet (created in Sub-Task 6)
- Base Docker network: `swarmnet` (bridge)
- Standard ports: Prometheus 9090, Grafana 3000, Loki 3100, Promtail 9080, node-exporter 9100, cAdvisor 8080
- Docker compose production file: `deploy/docker/docker-compose.production-realms2riches.yml`

**Status:** [ ] pending

---

## Sub-Task 5 — Alembic Initial Schema Migration File

**Intent:** With Alembic initialized (Sub-Task 2), generate the actual initial migration file that creates all database tables. This is the artifact that gets run as "Step 1: Run database migrations" in the deployment checklist.

**Expected Outcomes:**
- `alembic/versions/<timestamp>_initial_schema.py` — a proper Alembic migration with `upgrade()` and `downgrade()` functions for all 9 tables.
- Migration creates tables in correct dependency order (users → api_keys → company_tenants → deployments → etc.).
- `scripts/run_migrations.sh` — a shell script that sets `DATABASE_URL` from environment and runs `alembic upgrade head`.
- CI workflow `.github/workflows/ci.yml` updated to include a migration dry-run test step.

**Todo List:**
1. Confirm Alembic is set up (depends on Sub-Task 2).
2. Read `backend/db/models.py` in full to capture every column, FK, index, and constraint.
3. Write `alembic/versions/0001_initial_schema.py` with `upgrade()` using `op.create_table()` for each model in dependency order.
4. Write `downgrade()` that drops tables in reverse order.
5. Write `scripts/run_migrations.sh` that exports `DATABASE_URL` and calls `alembic upgrade head`.
6. Add migration test step to `.github/workflows/ci.yml` using a SQLite in-memory URL.

**Relevant Context:**
- All 9 models with full column specs documented above in Sub-Task 2
- FK dependency order: User first, then APIKey (FK→users), CompanyTenant, Deployment (FK→company_tenants), then Ticket, Project, Lead, UsageEvent, ProcessedEvent
- CI file: `.github/workflows/ci.yml`
- Reference SOP: `assets/sops/TEC_001_DB_SCHEMA_MIGRATION.md`

**Status:** [ ] pending

---

## Sub-Task 6 — Prometheus Alerting Rules

**Intent:** `monitoring/prometheus.yml` references `alerts/*.yml` but that directory does not exist. Create production-grade alerting rules covering the most critical failure scenarios: service downtime, high error rates, DB connection exhaustion, disk space, memory, and Stripe webhook failures.

**Expected Outcomes:**
- `monitoring/alerts/` directory created.
- `monitoring/alerts/service_alerts.yml` — alert rules for: backend down, redis down, postgres down, caddy down.
- `monitoring/alerts/performance_alerts.yml` — alert rules for: high HTTP error rate (5xx > 1%), p95 latency > 2s, high memory usage > 85%.
- `monitoring/alerts/infrastructure_alerts.yml` — alert rules for: disk > 80%, CPU > 90% sustained, container restarts > 3.
- Each rule uses Prometheus metric names consistent with what `backend/metrics.py` exports.

**Todo List:**
1. Read `backend/metrics.py` to identify exact metric names exported (counter names, histogram names, labels).
2. Read `monitoring/prometheus.yml` to confirm rule_files path pattern (`alerts/*.yml`).
3. Create `monitoring/alerts/service_alerts.yml` with `up == 0` rules for each scrape target.
4. Create `monitoring/alerts/performance_alerts.yml` using HTTP request duration histograms and error counters.
5. Create `monitoring/alerts/infrastructure_alerts.yml` using node-exporter and cAdvisor metrics.
6. Reference: `assets/sops/TEC_010_TELEMETRY_DASHBOARD.md`.

**Relevant Context:**
- Prometheus config: `monitoring/prometheus.yml` (scrapes backend:8000/metrics, postgres, redis, caddy:2019, node-exporter:9100, cAdvisor:8080)
- Backend metrics exposed at `/metrics` via `backend/metrics.py`
- Alert rule files path: `monitoring/alerts/*.yml`
- Alertmanager is commented out in `prometheus.yml` — Sub-Task 8 wires it up

**Status:** [ ] pending

---

## Sub-Task 7 — Grafana Dashboard Definitions

**Intent:** No Grafana dashboard JSON files exist. Create production-grade dashboard definitions for the three key views: system overview, API performance, and business metrics (deployments, leads, payments).

**Expected Outcomes:**
- `monitoring/grafana/dashboards/system_overview.json` — CPU, memory, disk, container uptime.
- `monitoring/grafana/dashboards/api_performance.json` — request rate, error rate, p50/p95/p99 latency by endpoint.
- `monitoring/grafana/dashboards/business_metrics.json` — deployment success rate, lead count, Stripe payment events.
- `monitoring/grafana/provisioning/dashboards/dashboard.yml` — Grafana dashboard provisioning config that auto-loads from the dashboards directory.
- Dashboards are compatible with Grafana 10.x and reference the Prometheus datasource by name `Prometheus`.

**Todo List:**
1. Read `backend/metrics.py` to capture all exported metric names and labels.
2. Read `monitoring/grafana/provisioning/datasources/datasources.yml` (created in Sub-Task 4) for datasource UID.
3. Write `monitoring/grafana/provisioning/dashboards/dashboard.yml` pointing to `/etc/grafana/dashboards`.
4. Write `monitoring/grafana/dashboards/system_overview.json` with panels for node metrics.
5. Write `monitoring/grafana/dashboards/api_performance.json` with request/latency panels.
6. Write `monitoring/grafana/dashboards/business_metrics.json` with deployment and lead panels.

**Relevant Context:**
- Grafana auto-provisioning: datasources at `monitoring/grafana/provisioning/datasources/`, dashboards at `monitoring/grafana/provisioning/dashboards/`
- Volume mapping in docker-compose.monitoring.yml (Sub-Task 4) mounts these directories into the Grafana container
- Grafana provisioning docs: https://grafana.com/docs/grafana/latest/administration/provisioning/
- Reference SOP: `assets/sops/TEC_010_TELEMETRY_DASHBOARD.md`

**Status:** [ ] pending

---

## Sub-Task 8 — Alertmanager Configuration

**Intent:** Prometheus alerting rules (Sub-Task 6) will fire alerts, but Alertmanager is commented out in `prometheus.yml`. Configure Alertmanager to route critical alerts to email (SMTP, already in `.env.example`) and provide a template for PagerDuty/Slack routing.

**Expected Outcomes:**
- `monitoring/alertmanager.yml` — Alertmanager config with: SMTP receiver using `SMTP_*` env vars, route tree (critical alerts → email immediately, warnings → email batched), inhibition rules.
- `monitoring/prometheus.yml` updated to uncomment the `alerting:` block pointing to `alertmanager:9093`.
- `deploy/docker/docker-compose.monitoring.yml` (Sub-Task 4) updated to add `alertmanager` service.

**Todo List:**
1. Read `monitoring/prometheus.yml` to find the commented alertmanager block.
2. Read `.env.example` SMTP section for variable names.
3. Write `monitoring/alertmanager.yml` with SMTP receiver using environment variable substitution.
4. Uncomment alertmanager block in `monitoring/prometheus.yml`.
5. Add alertmanager service to `deploy/docker/docker-compose.monitoring.yml`.
6. Reference: `assets/sops/SEC_007_RATE_LIMITING_SMTP.md` for SMTP security considerations.

**Relevant Context:**
- Prometheus alertmanager block (line 11-16 of `monitoring/prometheus.yml`) — commented out, target `alertmanager:9093`
- SMTP env vars: `SMTP_USER`, `SMTP_PASS`, `SMTP_SERVER` (default port 587)
- Depends on Sub-Task 4 (docker-compose.monitoring.yml) and Sub-Task 6 (alert rules exist)

**Status:** [ ] pending

---

## Sub-Task 9 — Monitoring Docker Compose Integration & Health Endpoint Verification

**Intent:** Ensure all monitoring services are wired into the compose stack, health endpoints are reachable, and a single `make monitoring-up` command brings up the full observability stack. Also verify the `/health` endpoint returns correct data for production.

**Expected Outcomes:**
- `make monitoring-up` successfully starts Prometheus, Grafana, Loki, Promtail, Alertmanager, node-exporter, cAdvisor.
- `GET /health` returns `{"status": "ONLINE", "version": "2.0.0", ...}`.
- `GET /metrics` returns Prometheus-formatted text.
- All compose service health checks pass.
- `scripts/smoke_monitoring.sh` — script that curls each monitoring endpoint and reports status.

**Todo List:**
1. Review `deploy/docker/docker-compose.monitoring.yml` (from Sub-Task 4) for completeness.
2. Verify volume mount paths are correct for all monitoring config files.
3. Write `scripts/smoke_monitoring.sh` that curls: backend/health, backend/metrics, prometheus:9090/-/healthy, grafana:3000/api/health, loki:3100/ready.
4. Update `scripts/prod_runbook.md` with monitoring startup procedure.
5. Verify Grafana can reach Prometheus and Loki by checking datasource provisioning.
6. Reference: `assets/sops/TEC_005_DOCKER_CONTAINER_UPKEEP.md`.

**Relevant Context:**
- Backend health endpoint: `GET /health` (line 152 `backend/main.py`)
- Backend metrics endpoint: `GET /metrics` (line 60 `backend/main.py`)
- Compose monitoring file created in Sub-Task 4
- Existing smoke test: `scripts/smoke_api.py`

**Status:** [ ] pending

---

## Sub-Task 10 — Automated Database Backup Script

**Intent:** No backup automation exists — only guidance in `scripts/prod_runbook.md`. Create a proper daily backup system using `pg_dump` that stores timestamped dumps, enforces a retention policy, and can restore from backup.

**Expected Outcomes:**
- `scripts/backup_postgres.sh` — shell script that: runs `pg_dump` via Docker exec, saves to `./backups/postgres/YYYY-MM-DD_HH-MM.sql.gz`, deletes dumps older than 30 days.
- `scripts/restore_postgres.sh` — shell script that takes a dump file path argument and restores.
- `scripts/backup_config.sh` — backs up `.env`, `deploy/Caddyfile`, `alembic/versions/`, `monitoring/*.yml` to `./backups/config/`.
- `deploy/docker/docker-compose.backup.yml` — optional compose service that runs the backup script on a cron schedule.
- `docs/guides/BACKUP_RECOVERY.md` — step-by-step backup and restore guide.

**Todo List:**
1. Read `scripts/prod_runbook.md` for existing backup guidance.
2. Read `docker-compose.yml` postgres service definition to get container name (`swarmOS-postgres`) and user/db env vars.
3. Write `scripts/backup_postgres.sh` using `docker exec swarmOS-postgres pg_dump`.
4. Write `scripts/restore_postgres.sh` with safety confirmation prompt.
5. Write `scripts/backup_config.sh` to snapshot all non-secret config files.
6. Write `docs/guides/BACKUP_RECOVERY.md` with RTO/RPO definitions and testing schedule.
7. Reference: `assets/sops/TEC_003_LOG_ROTATION.md` for retention policy patterns.

**Relevant Context:**
- Postgres container: `swarmOS-postgres` (from `docker-compose.yml` line 98)
- Postgres user/db from env: `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PASSWORD`
- Existing runbook: `scripts/prod_runbook.md`
- Backup path convention: `./backups/postgres/` and `./backups/config/`

**Status:** [ ] pending

---

## Sub-Task 11 — Disaster Recovery Runbook

**Intent:** The checklist requires a "Disaster Recovery Runbook" and "RTO/RPO defined." Create a practical DR document that covers the three failure scenarios most likely for this self-hosted stack: DB corruption, server loss, and application rollback.

**Expected Outcomes:**
- `docs/guides/DISASTER_RECOVERY.md` — full runbook with:
  - RTO: 2 hours, RPO: 24 hours (daily backup cadence)
  - Scenario 1: Database corruption → restore from backup
  - Scenario 2: Server/VM total loss → provision new VM, restore config, redeploy, restore DB
  - Scenario 3: Bad deployment → rollback to previous Docker image tag
  - Recovery testing schedule (monthly)
  - Contact escalation list placeholders
- `docs/PRE_LAUNCH_CHECKLIST.md` DR items updated.

**Todo List:**
1. Read `docs/guides/DEPLOYMENT_GUIDE.md` for current deployment procedure (to write accurate rollback steps).
2. Read `deploy/docker/docker-compose.production-realms2riches.yml` for image tag reference.
3. Read `.github/workflows/deploy.yml` for rollback strategy (image is tagged with `github.sha`).
4. Write `docs/guides/DISASTER_RECOVERY.md` with three scenario runbooks.
5. Define RTO (2h) and RPO (24h) based on daily backup schedule from Sub-Task 10.
6. Reference: `assets/sops/SELF_HEALING.md` for self-healing procedures.

**Relevant Context:**
- CD pipeline tags images with `:latest` and `:<github.sha>` (`.github/workflows/deploy.yml`)
- Docker Compose image field can be pinned to a specific SHA for rollback
- Backup scripts from Sub-Task 10 are the restore mechanism
- Self-healing agent: `agents/ops/scheduler.py` (auto-restarts failed containers)

**Status:** [ ] pending

---

## Sub-Task 12 — Security Hardening (Firewall, SSH, Infrastructure)

**Intent:** The application layer is hardened (HTTPS, CORS, JWT, RBAC) but infrastructure security items are unchecked: firewall rules, SSH key authentication, VPN for admin, intrusion detection, DDoS protection. Create the configuration files and documentation to complete these items.

**Expected Outcomes:**
- `deploy/firewall_rules.sh` — UFW/iptables script that: allows 80, 443 from any; allows 22 only from admin CIDR; blocks all other inbound ports; restricts Grafana (3000), Prometheus (9090) to internal network only.
- `deploy/ssh_hardening.conf` — sshd_config snippet: disable password auth, disable root login, require key auth.
- `docs/guides/SECURITY_HARDENING.md` — guide covering: firewall setup, SSH key deployment, VPN recommendation (WireGuard), DDoS protection (Cloudflare in front of Caddy), security update policy.
- `scripts/security_audit.sh` — script that checks: SSH password auth disabled, firewall active, Docker daemon not exposed on TCP, env secrets not in git history.

**Todo List:**
1. Read `deploy/Caddyfile` to understand what ports Caddy exposes.
2. Read `docker-compose.yml` to list all exposed ports.
3. Read `assets/sops/SEC_002_SANDBOX_ENFORCEMENT.md` and `SEC_003_PHISHING_DEFENSE.md`.
4. Write `deploy/firewall_rules.sh` — UFW rules with comments.
5. Write `deploy/ssh_hardening.conf` — sshd_config drop-in.
6. Write `docs/guides/SECURITY_HARDENING.md`.
7. Write `scripts/security_audit.sh` — quick checklist runner.
8. Reference: `assets/sops/SEC_001_SECRET_PROTECTION.md`, `SEC_004_IP_REPUTATION_MANAGEMENT.md`, `SEC_010_AUDIT_TRAIL_INTEGRITY.md`.

**Relevant Context:**
- Exposed ports: 80, 443 (Caddy), 8000 (backend — should be internal only behind Caddy), 3000 (Grafana — should be internal only), 9090 (Prometheus — internal only)
- Cloudflare Tunnel token: `CLOUDFLARE_TUNNEL_TOKEN` already in `.env.example` — can replace direct exposure
- SSH deploy already uses key auth (`.github/workflows/deploy.yml` uses `SSH_DEPLOY_PRIVATE_KEY`)

**Status:** [ ] pending

---

## Sub-Task 13 — CDN & Rate Limiting Configuration

**Intent:** Two performance checklist items are unchecked: "CDN for static assets" and "Rate limiting configured." The application has rate limiting middleware referenced in the checklist as ✅ but the Caddy config doesn't enforce it at the edge. Configure Caddy rate limiting and document CDN setup via Cloudflare.

**Expected Outcomes:**
- `deploy/Caddyfile` updated with rate limiting directives using the `caddy-ratelimit` plugin or `header`-based throttling.
- `docs/guides/CDN_SETUP.md` — guide for putting Cloudflare in front of Caddy: DNS orange-cloud, cache rules for static assets, firewall rules to only accept Cloudflare IPs.
- `deploy/Caddyfile` updated to serve `frontend/public/` static assets with long cache headers (`Cache-Control: max-age=31536000`).
- `monitoring/alerts/performance_alerts.yml` (Sub-Task 6) includes a rate-limit breach alert.

**Todo List:**
1. Read full `deploy/Caddyfile` and `deploy/Caddyfile.self-hosted`.
2. Read `backend/main.py` CORS and rate-limit middleware sections.
3. Add `rate_limit` or `@ratelimit` matcher to Caddy config for `/api/*` routes (e.g., 100 req/min per IP).
4. Add `Cache-Control` headers for static asset routes in Caddy.
5. Write `docs/guides/CDN_SETUP.md` with Cloudflare orange-cloud setup steps.
6. Reference: `assets/sops/SEC_007_RATE_LIMITING_SMTP.md`.

**Relevant Context:**
- Caddyfile: `deploy/Caddyfile` (37 lines, all routes defined)
- Backend rate limiting: check `backend/api/routes.py` or middleware for existing slowapi/fastapi-limiter config
- `CLOUDFLARE_TUNNEL_TOKEN` is already a supported env var — Cloudflare Tunnel eliminates the need for open inbound ports entirely

**Status:** [ ] pending

---

## Sub-Task 14 — Horizontal Scaling & Load Balancer Configuration

**Intent:** Scalability items for "Horizontal scaling ready," "Load balancer configuration," and "Auto-scaling policies" are unchecked. The application is already stateless (JWT auth, Redis for session state) — document and configure the scale-out path.

**Expected Outcomes:**
- `deploy/docker/docker-compose.scale.yml` — compose override that removes port binding from backend (load balancer handles it) and sets `deploy.replicas: 3` for backend service.
- `deploy/Caddyfile.lb` — Caddyfile variant using Caddy upstream with multiple backend instances for load balancing.
- `docs/guides/SCALING_GUIDE.md` — explains the scale-out path: (1) Docker Compose replicas, (2) Docker Swarm mode, (3) eventual Kubernetes. Includes `docker service scale` commands.
- `scripts/scale_check.sh` — verifies application is stateless: checks no local file-based session storage, confirms Redis URL is set, confirms DATABASE_URL points to a shared DB.

**Todo List:**
1. Read `backend/main.py` and `backend/db/base.py` to confirm no local state (file-based sessions, in-memory caches that break horizontal scale).
2. Read `deploy/Caddyfile` for upstream configuration syntax.
3. Write `deploy/docker/docker-compose.scale.yml` with replicas and no direct port exposure on backend.
4. Write `deploy/Caddyfile.lb` with upstream block listing multiple backend instances.
5. Write `docs/guides/SCALING_GUIDE.md`.
6. Write `scripts/scale_check.sh` stateless verification script.

**Relevant Context:**
- Redis for JWT revocation: `REDIS_URL` in `.env.example`
- SQLAlchemy DB sessions are stateless (no in-process session store)
- Backend port is `8000`, Caddy reverse proxies to it
- Docker Compose `deploy.replicas` works with Docker Swarm mode; document this distinction

**Status:** [ ] pending

---

## Sub-Task 15 — GDPR Compliance & Legal Pages

**Intent:** Compliance checklist items (GDPR reviewed, privacy policy published, terms published, data retention policy, user data export) are all unchecked. The `frontend/public/` directory has `privacy-policy.html` and `terms.html` stubs — these need to be completed with legally-adequate content and the backend needs a data export endpoint.

**Expected Outcomes:**
- `frontend/public/privacy-policy.html` — complete GDPR-compliant privacy policy for SwarmEnterprise (data collected, retention periods, right to erasure, right to export, DPO contact).
- `frontend/public/terms.html` — complete terms of service covering: platform use, payment terms, acceptable use, liability limitations.
- `backend/api/gdpr.py` — new router with `GET /api/user/export` (returns all user data as JSON) and `DELETE /api/user/account` (GDPR right to erasure — deletes user + all related data).
- `docs/guides/GDPR_COMPLIANCE.md` — compliance summary: what data is stored, legal basis, retention policy, DPO contact placeholder.
- `backend/main.py` updated to include the GDPR router.
- Reference: `assets/sops/SEC_005_DATA_PRIVACY_GDPR.md`.

**Todo List:**
1. Read `frontend/public/privacy-policy.html` and `frontend/public/terms.html` to see current stub content.
2. Read `backend/db/models.py` to identify all PII fields (User.email, User.full_name, Lead.email, Lead.name).
3. Read `assets/sops/SEC_005_DATA_PRIVACY_GDPR.md` for compliance procedure.
4. Write complete `privacy-policy.html` with GDPR-required sections.
5. Write complete `terms.html` with subscription/SaaS terms.
6. Write `backend/api/gdpr.py` with `/api/user/export` and `/api/user/account` DELETE endpoints.
7. Write `docs/guides/GDPR_COMPLIANCE.md`.
8. Register GDPR router in `backend/main.py`.

**Relevant Context:**
- PII in DB: User (email, full_name), Lead (email, name, company), Project (customer_email), UsageEvent (project_id)
- Frontend static files: `frontend/public/privacy-policy.html`, `frontend/public/terms.html`
- Authentication required for export/delete endpoints — use existing JWT auth from `backend/api/routes.py`
- Cascade deletes are defined on models — verify User deletion cascades to APIKey and related records

**Status:** [ ] pending

---

## Sub-Task 16 — Staging Smoke Test Script

**Intent:** The deployment checklist step 7 ("Test health endpoints") and post-deployment step ("Smoke test in production") have no automation. Create a comprehensive smoke test script that can run against any environment URL.

**Expected Outcomes:**
- `scripts/smoke_test.sh` — bash script accepting `BASE_URL` argument that tests: /health, /metrics, /api/auth/register (with test user), /api/auth/login, /api/companies (authenticated), /api/payments/plans, Caddy SSL (curl -I https://), Stripe webhook endpoint reachability.
- `scripts/smoke_api.py` (existing) updated/extended with the same tests in Python for richer assertion output.
- `docs/guides/DEPLOYMENT_GUIDE.md` updated with smoke test step referencing the script.
- All smoke test steps are documented with expected response codes and response body patterns.

**Todo List:**
1. Read `scripts/smoke_api.py` to understand existing tests and extend rather than duplicate.
2. Read `backend/api/routes.py` to list all available API endpoints and their expected responses.
3. Write `scripts/smoke_test.sh` with curl-based tests and exit-code-based pass/fail.
4. Extend `scripts/smoke_api.py` with auth flow, payment plans, and health checks.
5. Update `docs/guides/DEPLOYMENT_GUIDE.md` step 7 to reference smoke test scripts.

**Relevant Context:**
- Existing smoke test: `scripts/smoke_api.py`
- Health endpoint: `GET /health` returns `{"status": "ONLINE", ...}`
- Metrics endpoint: `GET /metrics` returns Prometheus text
- Auth endpoint: likely `POST /api/auth/register` and `POST /api/auth/login`
- Payment plans: likely `GET /api/payments/plans`

**Status:** [ ] pending

---

## Sub-Task 17 — Checklist Completion & Final Verdict Update

**Intent:** Once all preceding sub-tasks are complete, update `docs/PRE_LAUNCH_CHECKLIST.md` to mark every completed item, update the launch readiness score, and change the final verdict from "READY FOR STAGING" to "READY FOR PRODUCTION."

**Expected Outcomes:**
- `docs/PRE_LAUNCH_CHECKLIST.md` has all previously-unchecked items marked `[x]`.
- Launch Readiness Score updated: all Critical, High Priority, and Medium Priority items ✅.
- Final Verdict section updated: Infrastructure Readiness ✅ READY, Overall Status: **READY FOR PRODUCTION**.
- `docs/IMPLEMENTATION_SUMMARY.md` appended with a completion entry documenting what was built in this execution plan.

**Todo List:**
1. Read `docs/PRE_LAUNCH_CHECKLIST.md` in full.
2. Verify each sub-task output artifact exists before marking its item complete.
3. Update every `[ ]` item that has been addressed by preceding sub-tasks to `[x]`.
4. Update the Launch Readiness Score section.
5. Update the Final Verdict section to PRODUCTION READY.
6. Append completion summary to `docs/IMPLEMENTATION_SUMMARY.md`.

**Relevant Context:**
- All 17 sub-tasks above map to specific checklist items
- `docs/PRE_LAUNCH_CHECKLIST.md` — full file
- `docs/IMPLEMENTATION_SUMMARY.md` — existing summary file to append to

**Status:** [ ] pending

---

## Execution Notes for Orchestrator Mode

When running in Orchestrator mode, the following sub-tasks can execute **in parallel**:

**Wave 1 (no dependencies):**
- Sub-Task 1 (Assets Guide) — independent
- Sub-Task 2 (Alembic Setup) — independent
- Sub-Task 3 (Env & Secrets) — independent
- Sub-Task 6 (Alert Rules) — independent

**Wave 2 (depends on Wave 1):**
- Sub-Task 4 (Monitoring Compose) — after Sub-Task 6 (needs alerts dir)
- Sub-Task 5 (Initial Migration) — after Sub-Task 2 (needs Alembic init)
- Sub-Task 7 (Grafana Dashboards) — after Sub-Task 4 (needs provisioning dirs)
- Sub-Task 8 (Alertmanager) — after Sub-Task 6 (needs alert rules)
- Sub-Task 10 (Backup Scripts) — independent
- Sub-Task 11 (DR Runbook) — after Sub-Task 10 (references backup scripts)
- Sub-Task 12 (Security Hardening) — independent
- Sub-Task 13 (CDN & Rate Limiting) — independent
- Sub-Task 14 (Horizontal Scaling) — independent
- Sub-Task 15 (GDPR & Legal) — independent
- Sub-Task 16 (Smoke Tests) — independent

**Wave 3 (depends on Wave 2):**
- Sub-Task 9 (Monitoring Integration) — after Sub-Tasks 4, 7, 8
- Sub-Task 17 (Checklist Update) — after all others complete

---

## Files Created / Modified by This Plan

| File | Action | Sub-Task |
|------|--------|----------|
| `assets/ASSETS_README.md` | CREATE | 1 |
| `assets/registry.json` | UPDATE | 1 |
| `alembic.ini` | CREATE | 2 |
| `alembic/env.py` | CREATE | 2 |
| `alembic/versions/0001_initial_schema.py` | CREATE | 5 |
| `scripts/validate_env.py` | CREATE | 3 |
| `scripts/generate_secrets.py` | CREATE | 3 |
| `docs/guides/SECRETS_MANAGEMENT.md` | CREATE | 3 |
| `.env.example` | UPDATE | 3 |
| `deploy/docker/docker-compose.monitoring.yml` | CREATE | 4 |
| `monitoring/grafana/provisioning/datasources/datasources.yml` | CREATE | 4 |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | CREATE | 7 |
| `monitoring/grafana/dashboards/*.json` (x3) | CREATE | 7 |
| `monitoring/alerts/service_alerts.yml` | CREATE | 6 |
| `monitoring/alerts/performance_alerts.yml` | CREATE | 6 |
| `monitoring/alerts/infrastructure_alerts.yml` | CREATE | 6 |
| `monitoring/alertmanager.yml` | CREATE | 8 |
| `monitoring/prometheus.yml` | UPDATE | 8 |
| `scripts/backup_postgres.sh` | CREATE | 10 |
| `scripts/restore_postgres.sh` | CREATE | 10 |
| `scripts/backup_config.sh` | CREATE | 10 |
| `docs/guides/BACKUP_RECOVERY.md` | CREATE | 10 |
| `docs/guides/DISASTER_RECOVERY.md` | CREATE | 11 |
| `deploy/firewall_rules.sh` | CREATE | 12 |
| `deploy/ssh_hardening.conf` | CREATE | 12 |
| `docs/guides/SECURITY_HARDENING.md` | CREATE | 12 |
| `scripts/security_audit.sh` | CREATE | 12 |
| `docs/guides/CDN_SETUP.md` | CREATE | 13 |
| `deploy/Caddyfile` | UPDATE | 13 |
| `deploy/docker/docker-compose.scale.yml` | CREATE | 14 |
| `docs/guides/SCALING_GUIDE.md` | CREATE | 14 |
| `frontend/public/privacy-policy.html` | UPDATE | 15 |
| `frontend/public/terms.html` | UPDATE | 15 |
| `backend/api/gdpr.py` | CREATE | 15 |
| `backend/main.py` | UPDATE | 15 |
| `docs/guides/GDPR_COMPLIANCE.md` | CREATE | 15 |
| `scripts/smoke_test.sh` | CREATE | 16 |
| `scripts/smoke_api.py` | UPDATE | 16 |
| `docs/PRE_LAUNCH_CHECKLIST.md` | UPDATE | 17 |
| `docs/IMPLEMENTATION_SUMMARY.md` | UPDATE | 17 |

---

*Plan prepared by Bob — ready for Orchestrator mode execution.*
