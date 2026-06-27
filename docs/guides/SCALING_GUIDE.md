# SwarmEnterprise v2 — Horizontal Scaling Guide

This guide explains how SwarmEnterprise v2 is architected for horizontal scaling, how to
operate multiple backend replicas, and the path to more advanced orchestration.

---

## Table of Contents

1. [Why SwarmEnterprise Scales Horizontally](#1-why-swarmenterprise-scales-horizontally)
2. [Scaling with Docker Compose Replicas](#2-scaling-with-docker-compose-replicas)
3. [Load Balancer Configuration (Caddy)](#3-load-balancer-configuration-caddy)
4. [Upgrading to Docker Swarm Mode](#4-upgrading-to-docker-swarm-mode)
5. [Kubernetes Path](#5-kubernetes-path)
6. [Session Stickiness — Not Required](#6-session-stickiness--not-required)
7. [Database Connection Pooling at Scale](#7-database-connection-pooling-at-scale)
8. [Monitoring at Scale](#8-monitoring-at-scale)

---

## 1. Why SwarmEnterprise Scales Horizontally

Three architectural decisions make every backend replica fully independent:

### JWT — Stateless Authentication

All API authentication uses signed JWT tokens. The token payload carries the user identity
and is verified with a shared secret (`JWT_SECRET_KEY` from the environment). No replica
needs to ask another node "is this session valid?" — it reads the token and verifies the
signature locally.

```
Client  ──► Caddy (load balancer)
               ├─► backend_1  (verifies JWT locally)
               ├─► backend_2  (verifies JWT locally)
               └─► backend_3  (verifies JWT locally)
```

### Redis — Shared Token Revocation Store

When a token is invalidated (logout, forced expiry), the token ID (JTI) is written to the
shared Redis instance. Every replica checks this blocklist on every protected request, so a
token revoked against replica 1 is immediately rejected by replica 2 and replica 3.

Redis is the *only* cross-replica state store required for auth. It must be a single,
shared instance — **not** one Redis per replica.

### PostgreSQL — Single Source of Truth

All persistent application data (users, tenants, agents, outreach records) lives in a
single Postgres database that every replica connects to. Replicas are stateless application
servers; the database owns the state.

---

## 2. Scaling with Docker Compose Replicas

### Prerequisites

- Docker Compose v2.x (`docker compose version`)
- `.env` with `REDIS_URL` pointing to the shared Redis container (not `localhost`)
- `.env` with `DATABASE_URL` pointing to the shared Postgres instance (not `localhost`)
- Caddy running with `deploy/Caddyfile.lb` (see §3)

### Quick Scale

```bash
# Start the base stack + scale overlay (3 backend replicas, no direct port binding)
docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.scale.yml \
  up -d --scale backend=3
```

> **Note:** `deploy/docker/docker-compose.scale.yml` sets `ports: []` on the backend
> service, removing the direct `HOST:8000` binding. All traffic arrives through Caddy.
> Without this override the port binding conflicts when Docker tries to bind the same host
> port on three containers.

### Verify Replicas

```bash
docker compose ps
# Expect: backend-1, backend-2, backend-3 all "healthy"
```

### Scale Down

```bash
docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.scale.yml \
  up -d --scale backend=1
```

### Rolling Update

The `update_config` in the scale overlay enforces one-at-a-time rolling restarts with a
10-second delay between instances, so there is no downtime during image upgrades:

```bash
# Pull new image, then re-up with the overlay — Compose respects update_config
docker compose \
  -f docker-compose.yml \
  -f deploy/docker/docker-compose.scale.yml \
  up -d --scale backend=3
```

---

## 3. Load Balancer Configuration (Caddy)

`deploy/Caddyfile.lb` replaces the default `deploy/Caddyfile` when running scaled.

Key differences from the single-instance Caddyfile:

| Feature | `Caddyfile` (single) | `Caddyfile.lb` (scaled) |
|---|---|---|
| Upstream | `backend:8000` | `backend_1:8000 backend_2:8000 backend_3:8000` |
| Health checks | passive only | active `health_uri /health` every 15 s |
| lb_policy | n/a | `round_robin` |
| Failure handling | n/a | `fail_duration 30s`, `max_fails 3` |

### Mounting the LB Caddyfile

In `docker-compose.yml` the Caddy service mounts `./deploy/Caddyfile`. Override this with
an environment-specific override file or a bind-mount flag:

```bash
# One-liner: symlink before compose up
ln -sf Caddyfile.lb deploy/Caddyfile.active
# then mount ./deploy/Caddyfile.active in your override
```

Or add a `caddy` service override in `deploy/docker/docker-compose.scale.yml`:

```yaml
services:
  caddy:
    volumes:
      - ./deploy/Caddyfile.lb:/etc/caddy/Caddyfile:ro
```

---

## 4. Upgrading to Docker Swarm Mode

Docker Swarm is the zero-dependency path from Compose to a multi-host cluster. The
`deploy:` block already present in `deploy/docker/docker-compose.scale.yml` is native
Swarm syntax and is silently ignored by plain `docker compose`.

### Initialize a Single-Node Swarm

```bash
docker swarm init
```

For a multi-node swarm, note the join token printed and run it on each worker node:

```bash
docker swarm join --token <token> <manager-ip>:2377
```

### Deploy as a Stack

```bash
docker stack deploy \
  -c docker-compose.yml \
  -c deploy/docker/docker-compose.scale.yml \
  swarm
```

Swarm will now manage the 3 replicas across available nodes and will reschedule failed
containers automatically, respecting the `restart_policy` and `update_config` in the
scale overlay.

### Useful Swarm Commands

```bash
docker stack services swarm          # list services + replica counts
docker service logs swarm_backend    # aggregate logs across all backend replicas
docker service ps swarm_backend      # per-replica placement and state
docker service scale swarm_backend=5 # live replica adjustment
```

### Overlay Network

When running in Swarm mode, change the `swarmnet` network driver to `overlay` so
containers on different nodes can communicate:

```yaml
# In a swarm-specific override file
networks:
  swarmnet:
    driver: overlay
    attachable: true
```

---

## 5. Kubernetes Path

Kubernetes manifests would live in `deploy/k8s/`. The mapping from the current Compose
definition is straightforward:

| Compose concept | Kubernetes equivalent |
|---|---|
| `backend` service | `Deployment` (3 replicas) + `Service` (ClusterIP) |
| `redis` service | `Deployment` + `Service`, or managed Redis (e.g. ElastiCache) |
| `postgres` service | `StatefulSet` + `PersistentVolumeClaim`, or managed RDS |
| `caddy` service | `Ingress` controller (nginx, Traefik, or Caddy Ingress) |
| `.env` file | `Secret` + `ConfigMap` |
| `healthcheck` | `readinessProbe` + `livenessProbe` |

Suggested directory layout:

```
deploy/k8s/
  namespace.yaml
  backend/
    deployment.yaml      # image, envFrom secretRef, readinessProbe /health
    service.yaml         # ClusterIP :8000
    hpa.yaml             # HorizontalPodAutoscaler (CPU/memory triggers)
  redis/
    deployment.yaml
    service.yaml
  postgres/              # or just a Secret pointing at managed RDS
    secret.yaml
  ingress/
    ingress.yaml         # host routing matching Caddyfile.lb
```

A minimal `HorizontalPodAutoscaler` for the backend:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## 6. Session Stickiness — Not Required

> **TL;DR:** Sticky sessions are not needed and should not be configured.

SwarmEnterprise uses JWT Bearer tokens, not server-side sessions. There is no in-memory
session object that lives on a specific backend instance. Each request is self-contained:

1. Client sends `Authorization: Bearer <jwt>`
2. Any replica verifies the signature with the shared `JWT_SECRET_KEY`
3. Any replica checks the shared Redis blocklist for the JTI
4. Request is processed — replica has all the information it needs

Enabling sticky sessions (e.g. Caddy `lb_policy cookie`) would:
- Negate the benefit of multiple replicas during normal operation
- Create an outage for all sticky clients when one replica restarts
- Add unnecessary complexity to the load balancer

Do **not** add sticky session configuration.

---

## 7. Database Connection Pooling at Scale

Each replica opens its own pool of connections to Postgres. With 3 replicas and a pool
size of N, Postgres sees up to `3 × N` simultaneous connections.

### Current Pool Settings

The backend uses SQLAlchemy's async engine. Check `backend/db/session.py` for the active
`pool_size` and `max_overflow` values.

### Recommendations at Scale

| Replica count | Recommended `pool_size` | Notes |
|---|---|---|
| 1 | 10 | Default development setting |
| 3 | 5 | 3 × 5 = 15 connections — comfortable for Postgres default `max_connections=100` |
| 10+ | 3–5 + PgBouncer | Add a PgBouncer sidecar or separate container to multiplex connections |

### Adding PgBouncer

For 10+ replicas, add a PgBouncer container to the stack that proxies all backend
connections to Postgres. Backends connect to `pgbouncer:5432`; PgBouncer maintains a
small real connection pool to Postgres.

```yaml
# Sketch — add to docker-compose.yml
pgbouncer:
  image: bitnami/pgbouncer:latest
  environment:
    POSTGRESQL_HOST: postgres
    POSTGRESQL_PORT: 5432
    PGBOUNCER_DATABASE: "*"
    PGBOUNCER_POOL_MODE: transaction
    PGBOUNCER_MAX_CLIENT_CONN: 200
    PGBOUNCER_DEFAULT_POOL_SIZE: 20
  networks:
    - swarmnet
```

Then set `DATABASE_URL=postgresql+asyncpg://user:pass@pgbouncer:5432/swarm` in `.env`.

---

## 8. Monitoring at Scale

### Prometheus Scraping

Each backend replica exposes `/metrics` at its own container address. When running with
Docker Compose the replicas are named `<project>-backend-1`, `-2`, `-3`. Configure
Prometheus to scrape all of them:

```yaml
# prometheus.yml scrape config
scrape_configs:
  - job_name: backend
    static_configs:
      - targets:
          - backend_1:8000
          - backend_2:8000
          - backend_3:8000
    metrics_path: /metrics
```

In Docker Swarm / Kubernetes, use DNS-based service discovery so Prometheus picks up new
replicas automatically without a config change:

```yaml
# Swarm — scrape the service VIP; Prometheus sees all task IPs via DNS SRV
- job_name: backend
  dns_sd_configs:
    - names: ["tasks.backend"]
      type: SRV
```

### Useful Per-Instance Metrics

- **Request rate / latency** — `http_requests_total`, `http_request_duration_seconds`
- **Replica identity** — add an `instance` label to all metrics (Prometheus does this
  automatically from the scrape target address)
- **Database pool saturation** — `sqlalchemy_pool_size`, `sqlalchemy_pool_checked_out`
- **Redis latency** — track round-trip time for blocklist lookups

### Grafana Dashboard

When running multiple replicas, filter the "Backend" dashboard by `instance` to compare
load distribution. Unequal distributions usually indicate a problem with the load
balancer, not the application.

### Alerting

Add an alert when any replica is unhealthy for more than 30 seconds:

```yaml
# alerting rule
- alert: BackendReplicaDown
  expr: up{job="backend"} == 0
  for: 30s
  labels:
    severity: warning
  annotations:
    summary: "Backend replica {{ $labels.instance }} is down"
```
