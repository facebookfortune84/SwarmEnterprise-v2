Production runbook (SwarmOS)

1. Rotate secrets
   - Ensure STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, SMTP_PASS, OLLAMA_API_KEY, HUBSPOT_API_KEY, CLOSE_API_KEY, PAGERDUTY_ROUTING_KEY are stored in Secrets Manager or GitHub Secrets.

2. Infrastructure
   - Deploy docker-compose stack (or use Kubernetes): docker compose up -d
   - Required services: backend, redis, chromadb (if used), postgres/sqlite persisted volume

3. Workers
   - Start Celery worker: celery -A backend.celery_app.celery_app worker --loglevel=info
   - Ensure outreach worker runs if not using Celery (backend auto-starts in-process by default)

4. Monitoring
   - Configure OTEL_OTLP_ENDPOINT to your OTLP collector.
   - Configure Prometheus to scrape /metrics on backend host.
   - Configure PagerDuty routing key in PAGERDUTY_ROUTING_KEY.
   - See "Monitoring Startup Procedure" section below for the full bring-up checklist.

5. Backups
   - Backup pg_data and output directories regularly.

6. Incident response
   - If outreach failures spike, check SMTP provider health and rotate providers via SMTP_FALLBACKS.
   - For elevated error rates, use PagerDuty helper to create incidents.

7. CI/CD
   - Use GitHub Actions deploy workflow. Populate secrets: DOCKER_REGISTRY_USER, DOCKER_REGISTRY_PASSWORD, SSH_DEPLOY_*.

8. Git history purge
   - Use scripts/purge_secrets_instructions.md to remove leaked .env and rotate keys.

---

## Monitoring Startup Procedure

This section covers bringing up the full Prometheus/Grafana/Loki monitoring stack
and verifying that every component is healthy.

### 1. Start the monitoring stack

```bash
make monitoring-up
```

This runs:
```
docker compose -f docker-compose.yml -f deploy/docker/docker-compose.monitoring.yml up -d
```

Services started: **Prometheus** (9090), **Grafana** (3000), **Loki** (3100),
**Promtail**, **node-exporter** (9100), **cAdvisor** (8080), **Alertmanager** (9093).

### 2. Wait for first scrape

Prometheus scrapes the backend every **10 seconds** and all other targets every
**15 seconds**. Wait at least **30 seconds** after startup before running any
queries or smoke tests so that at least one scrape cycle has completed.

```bash
sleep 30
```

### 3. Run the monitoring smoke test

```bash
./scripts/smoke_monitoring.sh            # backend defaults to http://localhost:8000
./scripts/smoke_monitoring.sh https://realms2riches.com   # remote backend
```

The script tests all eight endpoints and exits **0** (all pass) or **1** (any
fail). Each line prints `[PASS]` or `[FAIL]` with the actual HTTP status code:

| Endpoint | Expected |
|---|---|
| `$BASE_URL/health` | 200, body contains `"ONLINE"` |
| `$BASE_URL/metrics` | 200, body contains `# HELP` |
| `http://localhost:9090/-/healthy` | 200 |
| `http://localhost:9090/-/ready` | 200 |
| `http://localhost:3000/api/health` | 200 |
| `http://localhost:3100/ready` | 200 |
| `http://localhost:9093/-/healthy` | 200 |
| `http://localhost:9100/metrics` | 200 |

### 4. Access Grafana

Open **http://localhost:3000** in a browser.

- **Username:** `admin`
- **Password:** value of `$GRAFANA_PASSWORD` env var (falls back to `admin` if unset)

Datasources are pre-provisioned via
`monitoring/grafana/provisioning/datasources/datasources.yml`:
- **Prometheus** (default) — `http://prometheus:9090`
- **Loki** — `http://loki:3100`

### 5. Check Prometheus scrape targets

Open **http://localhost:9090/targets**

All configured jobs (backend, node, prometheus, alertmanager, caddy, minio, …)
should show state **UP**. A target in state **DOWN** means the service is
unreachable from inside the Docker network — check that the container is running
(`docker compose ps`) and that the hostname matches the service name defined in
`docker-compose.yml`.

### 6. Check alert rules

Open **http://localhost:9090/alerts**

All rules loaded from `monitoring/alerts/*.yml` are listed here. Rules in state
**PENDING** have been firing for less than the `for:` duration; rules in state
**FIRING** are active and will have been forwarded to Alertmanager.

### 7. Silence an alert in Alertmanager

Open **http://localhost:9093**

To create a silence:
1. Click **Silences → New Silence**.
2. Add a matcher that identifies the alert, e.g. `alertname = HighErrorRate`.
3. Set **Start** and **End** times (ISO-8601 or relative, e.g. `+2h`).
4. Add a **Comment** describing why the alert is silenced and by whom.
5. Click **Create**.

To expire a silence early, find it in the **Silences** list and click **Expire**.

### 8. Tear down the monitoring stack

```bash
make monitoring-down
```
