# SwarmEnterprise v2 — Disaster Recovery Runbook

**Organization:** RWV Techsolutions LLC  
**Product:** SwarmEnterprise v2 / realms2riches.com  
**Document owner:** robertdemottojr50@gmail.com  
**Last reviewed:** <!-- update on each drill -->

---

## Recovery Objectives

| Metric | Target | Basis |
|--------|--------|-------|
| **RTO** (Recovery Time Objective) | **2 hours** | Time from incident declaration to services restored |
| **RPO** (Recovery Point Objective) | **24 hours** | Daily automated backup cadence (cron at 02:00 UTC) |

---

## Pre-Recovery Checklist

Complete this checklist **before** starting any recovery procedure.

- [ ] Confirm the incident is real and not a monitoring false-positive
- [ ] Check `https://api.realms2riches.com/health` — record the HTTP response code
- [ ] Run `docker compose ps` on the host — record which containers are `Up` vs `Exited`
- [ ] Identify the **most recent clean backup** in `/mnt/backups/swarm/` (or off-site copy)
- [ ] Confirm you have access to the secure `.env` / secrets backup
- [ ] Notify primary contact (see [Contact Escalation](#contact-escalation)) if RTO risk > 30 min
- [ ] Open a timestamped incident log (plain text file, Google Doc, etc.) — record every action taken
- [ ] Verify current disk space: `df -h` — ensure ≥ 5 GB free before restoring

---

## Scenario 1: Database Corruption

**Symptoms**

- PostgreSQL logs contain `ERROR`, `PANIC`, `invalid page`, or `could not read block`
- API endpoints return HTTP 500 with a database-related traceback
- `docker compose ps` shows the `postgres` container restarting or in an error state

**Expected recovery time:** 30 – 60 minutes

---

### Step 1 — Confirm the failure

```bash
# Check Postgres container state
docker compose ps postgres

# Tail Postgres logs for error messages
docker compose logs --tail=100 postgres
```

**Expected output:** Entries containing `ERROR` or `FATAL` lines pointing to page/heap corruption.

---

### Step 2 — Stop all application services (preserve the database volume)

```bash
# Stop backend and worker first — do NOT use -v (would destroy volumes)
docker compose stop backend worker ops-heal caddy
```

> ⚠️ Do **not** run `docker compose down -v` — that destroys the `pg_data_pg` volume.

---

### Step 3 — Identify the most recent backup

```bash
# List available backups, newest first
ls -lt /mnt/backups/swarm/postgres_*.sql.gz | head -10
```

Note the filename of the most recent backup, e.g. `postgres_20250714_020001.sql.gz`.

---

### Step 4 — Restore from backup

```bash
# Run the restore script (wraps pg_restore steps)
bash scripts/restore_postgres.sh /mnt/backups/swarm/postgres_20250714_020001.sql.gz
```

If `scripts/restore_postgres.sh` is unavailable, execute manually:

```bash
# Drop the corrupted database and recreate it
docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" swarmOS-postgres \
    psql -U "${POSTGRES_USER:-swarm}" -c "DROP DATABASE IF EXISTS swarm;"

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD}" swarmOS-postgres \
    psql -U "${POSTGRES_USER:-swarm}" -c "CREATE DATABASE swarm;"

# Decompress and pipe the dump into the fresh database
gunzip -c /mnt/backups/swarm/postgres_20250714_020001.sql.gz | \
    docker exec -i swarmOS-postgres \
    psql -U "${POSTGRES_USER:-swarm}" -d swarm
```

**Expected output:** No ERROR lines during restore; final line is `SET` or similar completion marker.

---

### Step 5 — Verify data integrity

```bash
# Spot-check row counts in key tables
docker exec swarmOS-postgres \
    psql -U "${POSTGRES_USER:-swarm}" -d swarm \
    -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;"

# Run Alembic to confirm schema is at latest revision
export DATABASE_URL="postgresql://${POSTGRES_USER:-swarm}:${POSTGRES_PASSWORD}@localhost:5432/swarm"
make db-upgrade
```

**Expected output:** Row counts are plausible; Alembic reports `INFO  [alembic.runtime.migration] Running upgrade ...` (or `Target database is up to date`).

---

### Step 6 — Restart all services

```bash
# Production (realms2riches profile)
docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.production-realms2riches.yml \
  --profile proxy --profile postgres \
  up -d
```

---

### Step 7 — Verify services are healthy

```bash
# All containers should show healthy/running
docker compose ps

# Backend health endpoint
curl -sf https://api.realms2riches.com/health && echo "OK"
```

**Expected output:** All services `Up (healthy)`; health endpoint returns `200 OK`.

---

## Scenario 2: Server / VM Total Loss

**Symptoms**

- VPS is unreachable via SSH
- Provider dashboard shows the VM as stopped, destroyed, or unrecoverable
- All services are offline

**Expected recovery time:** 1.5 – 2 hours

---

### Step 1 — Provision a new VPS

Recommended spec: **Ubuntu 22.04 LTS**, 2 vCPU, 4 GB RAM, 40 GB SSD (minimum).

```bash
# After SSH access is confirmed:
ssh root@<NEW_SERVER_IP>

# Update base system
apt-get update && apt-get upgrade -y
```

---

### Step 2 — Install Docker and Docker Compose

```bash
# Install Docker Engine (official script)
curl -fsSL https://get.docker.com | sh

# Add your deploy user to the docker group
usermod -aG docker $USER

# Verify
docker --version
docker compose version
```

**Expected output:** Both commands return version strings (Docker ≥ 24, Compose ≥ 2.x).

---

### Step 3 — Clone the repository

```bash
# Install git if not present
apt-get install -y git

# Clone the project
git clone https://github.com/realms2riches/SwarmEnterprise-v2.git /opt/SwarmEnterprise-v2
cd /opt/SwarmEnterprise-v2
```

> 📌 Adjust the remote URL if the repo has moved.

---

### Step 4 — Restore the `.env` file from secure backup

```bash
# Copy from your secure off-site backup location, e.g.:
scp backup-store:/secure/.env /opt/SwarmEnterprise-v2/.env

# Verify critical variables are present
grep -E "DATABASE_URL|POSTGRES_PASSWORD|JWT_SECRET" .env
```

> ⚠️ Never commit `.env` to git. It must come from a separately secured backup (password manager, encrypted S3 object, or vault).

---

### Step 5 — Restore config backup

```bash
# Create the expected directory structure
mkdir -p /opt/SwarmEnterprise-v2/backups/config

# Copy the latest config backup from off-site storage
scp -r backup-store:/backups/config/* /opt/SwarmEnterprise-v2/backups/config/

# Or re-generate from the current repo state if the config backup is unavailable:
bash scripts/backup_config.sh
```

Configs restored here include: `deploy/Caddyfile`, `monitoring/` provisioning files, and any
tenant-specific overrides stored under `backups/config/`.

---

### Step 6 — Apply database migrations

```bash
cd /opt/SwarmEnterprise-v2

# Export the connection string so Alembic and make can find it
export DATABASE_URL="postgresql://${POSTGRES_USER:-swarm}:${POSTGRES_PASSWORD}@localhost:5432/swarm"

# Start only the Postgres container first, then apply migrations
docker compose \
  -f docker-compose.yml \
  --profile postgres \
  up -d postgres

# Wait for Postgres to be healthy
until docker compose exec postgres pg_isready -U "${POSTGRES_USER:-swarm}"; do
  echo "Waiting for Postgres..."; sleep 3
done

make db-upgrade
```

**Expected output:** `INFO  [alembic.runtime.migration] Running upgrade ...` followed by `Target database is up to date`.

---

### Step 7 — Restore the latest database backup

```bash
# List available backups (from off-site restore or /mnt/backups/swarm/)
ls -lt /mnt/backups/swarm/postgres_*.sql.gz | head -5

# Restore
bash scripts/restore_postgres.sh /mnt/backups/swarm/postgres_<DATE>.sql.gz

# Or manually (see Scenario 1 Step 4 for the full manual procedure)
```

---

### Step 8 — Bring the full production stack up

```bash
cd /opt/SwarmEnterprise-v2

docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.production-realms2riches.yml \
  --profile proxy --profile postgres \
  up -d
```

This is equivalent to `make docker-up-prod` (see [`Makefile`](../../Makefile:43)).

---

### Step 9 — Verify full service health

```bash
# All containers running
docker compose ps

# Backend API
curl -sf https://api.realms2riches.com/health && echo "OK"

# Check Caddy acquired SSL certificates (may take 60 s on first boot)
docker compose logs caddy | grep -i "certificate\|tls\|acme"

# Spot-check a DB query
docker exec swarmOS-postgres \
    psql -U "${POSTGRES_USER:-swarm}" -d swarm -c "SELECT COUNT(*) FROM information_schema.tables;"
```

**Expected output:** All services `Up (healthy)`; API returns `200`; Caddy logs show `certificate obtained successfully`.

---

## Scenario 3: Bad Deployment / Rollback

**Symptoms**

- Health checks started failing immediately after a `docker compose pull && docker compose up -d`
- Error rate spiked post-deploy; logs show application-level exceptions tied to the new image
- `docker compose ps` shows `backend` restarting in a loop

**Expected recovery time:** 5 – 15 minutes

---

### Step 1 — Identify the bad image SHA from the deploy log

```bash
# Find the SHA of the currently running (bad) image
docker inspect swarmOS-backend --format '{{.Image}}'
# Example output: sha256:c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2

# Find the previous known-good image SHA from Docker image history
docker images ghcr.io/realms2riches/swarmenterprise-backend --digests
```

Note the **previous** `IMAGE ID` or digest — that is your rollback target.

---

### Step 2 — Pin the compose file to the previous image SHA

The production image tag is controlled by the `BACKEND_IMAGE` variable in
[`deploy/docker/docker-compose.production-realms2riches.yml`](../../../deploy/docker/docker-compose.production-realms2riches.yml:4):

```yaml
image: ${BACKEND_IMAGE:-ghcr.io/realms2riches/swarmenterprise-backend:latest}
```

Override it with the previous known-good SHA:

```bash
# Option A — environment variable override (no file edit needed)
export BACKEND_IMAGE="ghcr.io/realms2riches/swarmenterprise-backend@sha256:<PREVIOUS_SHA>"

# Option B — edit the compose file directly
# Replace the image line with the pinned digest:
#   image: ghcr.io/realms2riches/swarmenterprise-backend@sha256:<PREVIOUS_SHA>
```

---

### Step 3 — Pull the pinned image and redeploy

```bash
docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.production-realms2riches.yml \
  --profile proxy --profile postgres \
  pull

docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.production-realms2riches.yml \
  --profile proxy --profile postgres \
  up -d
```

---

### Step 4 — Confirm rollback succeeded

```bash
# Verify the running image matches the pinned SHA
docker inspect swarmOS-backend --format '{{.Image}}'

# Health check
curl -sf https://api.realms2riches.com/health && echo "OK"

# Watch logs for 60 seconds for error recurrence
docker compose logs -f --tail=50 backend
```

**Expected output:** Health endpoint returns `200`; no exception tracebacks in log tail.

---

### Step 5 — After stabilising

- Open a GitHub issue (or internal ticket) documenting the bad image SHA and the symptoms.
- Re-pin `BACKEND_IMAGE` in `.env` or the compose file until the root cause is fixed.
- Do **not** unset the pin until a new image is tested in a staging environment.

---

## Recovery Testing Schedule

Regular fire drills prevent the runbook from going stale and ensure the team can execute under pressure.

### Monthly Drill (first Friday of each month)

| # | Test | Pass Criteria |
|---|------|---------------|
| 1 | **Backup integrity** — decompress latest `postgres_*.sql.gz` into a throwaway DB | Restore completes without errors; row counts match production snapshot |
| 2 | **Rollback drill** — deploy a dummy "bad" image tag and execute Scenario 3 | Services restored within 15 min |
| 3 | **Config restore** — delete local `backups/config/` and re-run `scripts/backup_config.sh` | All config files regenerated correctly |
| 4 | **Health-check verification** — stop one service and confirm alerting fires | Alert received within 5 min; Grafana dashboard reflects the outage |

### Quarterly Drill (once per quarter)

| # | Test | Pass Criteria |
|---|------|---------------|
| 1 | **Full VM restore** — provision a clean VM and execute Scenario 2 end-to-end | Full stack healthy within 2 hours; all data present |
| 2 | **Database corruption drill** — corrupt a test DB page and execute Scenario 1 | Services restored within 60 min; data loss ≤ 24 h |

### Drill Log

Keep a running log at `docs/drills/DRILL_LOG.md` with date, scenario tested, actual recovery time, and any runbook gaps found.

---

## Contact Escalation

| Role | Contact | When to escalate |
|------|---------|-----------------|
| **Primary on-call** | robertdemottojr50@gmail.com | Immediately upon incident declaration |
| **Organization** | RWV Techsolutions LLC | Incidents exceeding RTO or requiring vendor/provider action |
| **VPS provider support** | *(add provider portal URL)* | VM-level failures requiring hypervisor intervention |
| **Domain/DNS registrar** | *(add registrar support URL)* | DNS hijack, zone corruption, or SSL CA issues |

> 📌 If paging fails after 15 minutes, escalate to the next contact. Include the incident log URL in all escalation messages.

---

## Reference: Key File Locations

| Resource | Path |
|----------|------|
| Base compose stack | [`docker-compose.yml`](../../docker-compose.yml) |
| Production overlay | [`deploy/docker/docker-compose.production-realms2riches.yml`](../../deploy/docker/docker-compose.production-realms2riches.yml) |
| Environment file | `.env` (never committed — restore from secure backup) |
| Postgres restore script | `scripts/restore_postgres.sh` |
| Config backup script | `scripts/backup_config.sh` |
| Config backup archive | `./backups/config/` |
| Automated backup script | `~/backup-swarm.sh` (see [Deployment Guide](./DEPLOYMENT_GUIDE.md)) |
| Backup destination | `/mnt/backups/swarm/` |
| Alembic migrations | `alembic/versions/` |
| Makefile targets | [`Makefile`](../../Makefile) |

---

*This runbook was authored as Sub-Task 11 of the SwarmEnterprise v2 Launch Execution Plan.*  
*Review and update after every production incident and every quarterly drill.*
