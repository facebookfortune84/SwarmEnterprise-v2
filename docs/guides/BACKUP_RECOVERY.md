# Backup & Recovery Guide — SwarmOS

> **RTO (Recovery Time Objective): 2 hours**  
> **RPO (Recovery Point Objective): 24 hours**

---

## Table of Contents

1. [Overview](#1-overview)
2. [What Gets Backed Up](#2-what-gets-backed-up)
3. [Running Backups Manually](#3-running-backups-manually)
4. [Automated Backup Schedule](#4-automated-backup-schedule)
5. [Restoring from a Database Backup](#5-restoring-from-a-database-backup)
6. [Restoring from a Config Backup](#6-restoring-from-a-config-backup)
7. [Retention Policy](#7-retention-policy)
8. [Verifying a Backup](#8-verifying-a-backup)
9. [Monthly Testing Schedule](#9-monthly-testing-schedule)
10. [Backup Storage Recommendations](#10-backup-storage-recommendations)

---

## 1. Overview

SwarmOS uses three shell scripts to protect production data:

| Script | Purpose |
|---|---|
| [`scripts/backup_postgres.sh`](../../scripts/backup_postgres.sh) | Hot pg_dump of the running Postgres container, gzip-compressed |
| [`scripts/restore_postgres.sh`](../../scripts/restore_postgres.sh) | Restore a `.sql.gz` dump back into the container |
| [`scripts/backup_config.sh`](../../scripts/backup_config.sh) | Snapshot of all configuration files into a `.tar.gz` archive |

Automated daily execution is handled by the  
[`deploy/docker/docker-compose.backup.yml`](../../deploy/docker/docker-compose.backup.yml) `backup-cron` service.

---

## 2. What Gets Backed Up

### Database backup (`backup_postgres.sh`)

- Full logical dump of the `${POSTGRES_DB}` database (default: `swarm`)
- Produced by `pg_dump` inside the `swarmOS-postgres` container
- Output: `./backups/postgres/YYYY-MM-DD_HH-MM.sql.gz`

### Config backup (`backup_config.sh`)

| File / Directory | Notes |
|---|---|
| `.env` | All runtime secrets and settings |
| `deploy/Caddyfile` | Public TLS + reverse-proxy config |
| `deploy/Caddyfile.self-hosted` | Self-hosted variant (if present) |
| `alembic/versions/` | Database migration history (if present) |
| `monitoring/*.yml` | Prometheus, Loki, Promtail configs |

Output: `./backups/config/YYYY-MM-DD_HH-MM.tar.gz`

---

## 3. Running Backups Manually

All scripts must be executed from the **project root** or will locate it automatically.

### 3.1 Database backup

```bash
bash scripts/backup_postgres.sh
```

Expected output:

```
[backup_postgres] Starting pg_dump for db='swarm' user='swarm' → /…/backups/postgres/2025-07-04_14-30.sql.gz
[backup_postgres] Dump complete: /…/backups/postgres/2025-07-04_14-30.sql.gz (2.1M)
[backup_postgres] Pruning dumps older than 30 days...
[backup_postgres] Done.
```

### 3.2 Config backup

```bash
bash scripts/backup_config.sh
```

Expected output:

```
[backup_config] Collecting files → /…/backups/config/2025-07-04_14-30
  [ok] .env
  [ok] deploy/Caddyfile
  [ok] deploy/Caddyfile.self-hosted
  [ok] monitoring/prometheus.yml
  [ok] monitoring/loki-config.yml
  [ok] monitoring/promtail-config.yml
[backup_config] Compressing → /…/backups/config/2025-07-04_14-30.tar.gz
[backup_config] Archive: /…/backups/config/2025-07-04_14-30.tar.gz (48K)
[backup_config] Done.
```

### 3.3 Both at once (pre-deployment snapshot)

```bash
bash scripts/backup_postgres.sh && bash scripts/backup_config.sh
```

---

## 4. Automated Backup Schedule

The `backup-cron` service in  
[`deploy/docker/docker-compose.backup.yml`](../../deploy/docker/docker-compose.backup.yml)  
runs `backup_postgres.sh` **every day at 02:00 UTC**.

### Starting the cron service

```bash
docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.backup.yml \
  up -d backup-cron
```

### Checking cron logs

```bash
docker exec swarmOS-backup-cron cat /var/log/backup_postgres.log
```

### Stopping the cron service

```bash
docker compose -f deploy/docker/docker-compose.backup.yml down
```

---

## 5. Restoring from a Database Backup

> ⚠️ **This is a destructive operation.** The target database will be **dropped and recreated**.  
> Ensure no application traffic is hitting the database before proceeding.

### Step-by-step

**Step 1 — Identify the dump file to restore**

```bash
ls -lh backups/postgres/
# Example: 2025-07-03_02-00.sql.gz
```

**Step 2 — Stop application services to prevent writes**

```bash
docker compose stop backend worker
```

**Step 3 — Run the restore script**

```bash
bash scripts/restore_postgres.sh backups/postgres/2025-07-03_02-00.sql.gz
```

You will see the warning banner and be prompted:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠  WARNING — DESTRUCTIVE OPERATION                            │
│  This will DROP and RECREATE the database 'swarm' …            │
└─────────────────────────────────────────────────────────────────┘

Type YES to continue: YES
```

Type `YES` (all caps) and press Enter.

**Step 4 — Verify the restore**

```bash
docker exec swarmOS-postgres psql -U swarm -d swarm -c "\dt"
```

You should see the full list of application tables.

**Step 5 — Restart application services**

```bash
docker compose start backend worker
```

**Step 6 — Smoke test**

```bash
curl -f http://localhost:8000/health
```

Expected: `{"status":"ok"}` or equivalent.

### Rollback

If the restore itself fails, the database may be in an empty state. Re-run the restore script with the same (or a prior) dump file. The script is idempotent — it drops and recreates the DB before loading.

---

## 6. Restoring from a Config Backup

**Step 1 — Locate the archive**

```bash
ls -lh backups/config/
# Example: 2025-07-03_02-00.tar.gz
```

**Step 2 — Extract to a staging directory**

```bash
mkdir -p /tmp/config-restore
tar -xzf backups/config/2025-07-03_02-00.tar.gz -C /tmp/config-restore
```

**Step 3 — Review the extracted files**

```bash
find /tmp/config-restore -type f
```

**Step 4 — Selectively or fully restore**

```bash
# Restore .env
cp /tmp/config-restore/2025-07-03_02-00/.env .env

# Restore Caddyfile
cp /tmp/config-restore/2025-07-03_02-00/deploy/Caddyfile deploy/Caddyfile

# Restore monitoring configs
cp /tmp/config-restore/2025-07-03_02-00/monitoring/*.yml monitoring/
```

**Step 5 — Reload affected services**

```bash
docker compose restart caddy
docker compose restart backend
```

---

## 7. Retention Policy

| Backup type | Location | Retained for |
|---|---|---|
| Database dumps | `backups/postgres/*.sql.gz` | **30 days** |
| Config archives | `backups/config/*.tar.gz` | Manual (no auto-prune) |

`backup_postgres.sh` automatically deletes dumps older than 30 days each time it runs.  
Config archives should be pruned manually or via a separate scheduled task to stay within disk budget.

### Recommended off-site retention

| Tier | Destination | Frequency |
|---|---|---|
| Daily | Local NVMe / SSD (on the host) | Automatic (cron) |
| Weekly | Object storage (S3 / Backblaze B2 / Wasabi) | `rclone sync` cron |
| Monthly | Cold storage (Glacier / deep archive) | Manual or lifecycle rule |

---

## 8. Verifying a Backup

### Quick integrity check (gzip header)

```bash
gzip -t backups/postgres/2025-07-03_02-00.sql.gz && echo "OK"
```

### Smoke-restore into a temporary container

This is the gold-standard verification — it proves the dump is actually restorable without touching production:

```bash
# 1. Spin up a disposable Postgres instance
docker run --rm -d \
  --name pg-verify \
  -e POSTGRES_USER=swarm \
  -e POSTGRES_PASSWORD=swarm \
  -e POSTGRES_DB=swarm_verify \
  postgres:16-alpine

# Wait for it to be ready
sleep 5

# 2. Restore the dump
gunzip -c backups/postgres/2025-07-03_02-00.sql.gz \
  | docker exec -i pg-verify psql -U swarm -d swarm_verify -q

# 3. Spot-check row counts
docker exec pg-verify psql -U swarm -d swarm_verify \
  -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;"

# 4. Tear down
docker stop pg-verify
```

### Config archive check

```bash
tar -tzf backups/config/2025-07-03_02-00.tar.gz | head -20
```

All expected paths (`.env`, `deploy/Caddyfile`, `monitoring/*.yml`) should appear in the listing.

---

## 9. Monthly Testing Schedule

A full restore drill should be performed **once per calendar month** in a staging environment:

| Step | Action | Owner |
|---|---|---|
| 1 | Pick the most recent database dump | On-call engineer |
| 2 | Smoke-restore into a disposable container (§8) | On-call engineer |
| 3 | Record the wall-clock time from step 2 start to "`\dt`" success | On-call engineer |
| 4 | Verify result is within the 2-hour RTO | Engineering lead |
| 5 | Extract the most recent config archive and diff against live files | On-call engineer |
| 6 | Document results in the team incident log | On-call engineer |

**Acceptance criteria**

- Full restore completes in < 2 hours (RTO)
- Restored table row counts are ≥ 95 % of production counts at dump time
- No `ERROR:` lines in the psql restore output
- Config archive contains `.env`, both Caddyfiles, and all monitoring YAMLs

---

## 10. Backup Storage Recommendations

```
backups/
├── postgres/
│   ├── 2025-07-01_02-00.sql.gz   ← daily dumps (auto-pruned at 30 days)
│   ├── 2025-07-02_02-00.sql.gz
│   └── …
└── config/
    ├── 2025-07-01_02-00.tar.gz   ← config snapshots (manual retention)
    └── …
```

> **Important:** The `backups/` directory should be added to `.gitignore` and **never committed to source control**, as `.env` snapshots contain secrets.

Add to `.gitignore`:

```
backups/
```

For off-site replication, configure `rclone` with a daily cron after the backup scripts run:

```bash
# Example: sync to an S3-compatible bucket
rclone sync ./backups/ remote:swarm-backups/$(hostname)/
```
