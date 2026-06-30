# 🚀 SwarmEnterprise v2 Launch Architecture

## System Topology: Windows 11 + Ubuntu Hyper-V

```
╔════════════════════════════════════════════════════════════════════════╗
║                          WINDOWS 11 PRO                               ║
║                          (Host Machine)                               ║
║                                                                        ║
║  ┌─────────────────┐                                                  ║
║  │   PowerShell    │  ←  Enable Hyper-V                              ║
║  │   WSL/SSH       │  ←  Connect to Ubuntu VM                        ║
║  │   Web Browser   │  ←  Access http://192.168.1.100:8000           ║
║  └─────────────────┘                                                  ║
║         ↓                                                              ║
║  ┌──────────────────────────────────────────────────────┐            ║
║  │         Hyper-V Hypervisor (Virtualization)         │            ║
║  └──────────────────────────────────────────────────────┘            ║
║         ↓                                                              ║
╚════════════════════════════════════════════════════════════════════════╝
         ↓
         ↓  (Virtual Machine)
         ↓
╔════════════════════════════════════════════════════════════════════════╗
║                     UBUNTU 22.04 LTS (VM)                             ║
║                     [4 vCPU, 8GB RAM, 80GB SSD]                       ║
║                                                                        ║
║  ┌────────────────────────────────────────────────────────────────┐  ║
║  │  SSH Server (openssh-server)                                   │  ║
║  │  ↑                                                              │  ║
║  │  └─ Accepts SSH connections from Windows PowerShell            │  ║
║  └────────────────────────────────────────────────────────────────┘  ║
║         ↓                                                              ║
║  ┌────────────────────────────────────────────────────────────────┐  ║
║  │  Docker Daemon (dockerd)                                       │  ║
║  │  ├─ Docker image registry                                      │  ║
║  │  ├─ Container orchestration                                    │  ║
║  │  └─ Network bridge (docker0)                                   │  ║
║  └────────────────────────────────────────────────────────────────┘  ║
║         ↓                                                              ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐            ║
║  │ PostgreSQL   │  │    Redis     │  │  FastAPI Backend │            ║
║  │   :5432      │  │   :6379      │  │      :8000       │            ║
║  │              │  │              │  │                  │            ║
║  │ (5GB volume) │  │ (persistence)│  │  (/opt/swarm)   │            ║
║  └──────────────┘  └──────────────┘  └──────────────────┘            ║
║         ↑                  ↑                    ↑                      ║
║         └─────────────────┴────────────────────┘                      ║
║                        ↓                                               ║
║         All connected via Docker bridge network                       ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
         ↓  Port 8000 exposed
         ↓
╔════════════════════════════════════════════════════════════════════════╗
║              Access from Windows Browser/PowerShell                   ║
║                  http://192.168.1.100:8000                            ║
╚════════════════════════════════════════════════════════════════════════╝
```

---

## Installation Flow

```
START (Windows 11 Pro)
  ↓
  Enable Hyper-V
  ↓
  Create Ubuntu VM (8GB, 80GB, 4CPU)
  ↓
  Install Ubuntu 22.04 LTS
  ↓
  Boot Ubuntu, get IP (e.g., 192.168.1.100)
  ↓
  SSH from Windows: ssh ubuntu@192.168.1.100
  ↓
  Download & run: bash launch_ubuntu.sh
  ↓
  ┌─────────────────────────────────────┐
  │ Automated Installation (~15 min):    │
  ├─────────────────────────────────────┤
  │ ✓ apt update/upgrade                │
  │ ✓ Docker install + Docker Compose   │
  │ ✓ Python 3.11 install               │
  │ ✓ Git install                       │
  │ ✓ Clone SwarmEnterprise repo        │
  │ ✓ Generate secrets (.env)           │
  │ ✓ Start PostgreSQL container        │
  │ ✓ Start Redis container             │
  │ ✓ Run Alembic migrations            │
  │ ✓ Seed initial data                 │
  │ ✓ Start FastAPI backend             │
  │ ✓ Health checks                     │
  └─────────────────────────────────────┘
  ↓
  LAUNCH COMPLETE!
  ↓
  Access: http://192.168.1.100:8000
  ↓
  DONE 🚀
```

---

## Command Quick Reference

### On WINDOWS (PowerShell)

| Action | Command |
|--------|---------|
| **Enable Hyper-V** | `Enable-WindowsOptionalFeature -FeatureName Hyper-V -Online -All` |
| **Connect to Ubuntu** | `ssh ubuntu@192.168.1.100` |
| **Copy files** | `scp -r "file" ubuntu@192.168.1.100:/home/ubuntu/` |
| **Start VM** | `Start-VM -Name swarmenterprise-vm` |
| **Stop VM** | `Stop-VM -Name swarmenterprise-vm` |
| **VM Status** | `Get-VM swarmenterprise-vm` |
| **Test API** | `Invoke-RestMethod http://192.168.1.100:8000/health` |
| **Open Swagger** | `Start-Process http://192.168.1.100:8000/docs` |

### On UBUNTU (Bash)

| Action | Command |
|--------|---------|
| **Activate** | Already running (Docker-based) |
| **Check services** | `docker compose ps` |
| **View logs** | `docker compose logs -f backend` |
| **Stop all** | `docker compose down` |
| **Start all** | `docker compose up -d` |
| **Restart backend** | `docker compose restart backend` |
| **Test API** | `curl http://localhost:8000/health` |
| **Database shell** | `docker compose exec postgres psql -U postgres` |
| **Redis shell** | `docker compose exec redis redis-cli` |
| **System info** | `docker stats --no-stream` |

---

## Key Network Connections

```
Windows 11 Host
  │
  ├─→ [SSH] ssh ubuntu@192.168.1.100:22
  │   (Remote command execution)
  │
  └─→ [HTTP] http://192.168.1.100:8000
      (API access)
          │
          ├─→ FastAPI Backend
          │     ├─→ PostgreSQL :5432
          │     ├─→ Redis :6379
          │     └─→ Task Queue
          │
          └─→ Swagger UI
                └─→ Interactive API docs
```

---

## What Runs Where

### On Windows 11
- PowerShell terminal
- SSH client
- Web browser
- File manager
- Hyper-V Manager

### On Ubuntu VM (In Docker)
```
Container 1: PostgreSQL 16
Container 2: Redis 7
Container 3: FastAPI Backend
(Optional) Container 4+: Celery Workers
```

---

## File Locations

### On Windows
```
C:\SwarmEnterprise-v2\            ← Your repo copy
├── START_HERE.md                 ← Read this first!
├── WINDOWS_UBUNTU_LAUNCH_GUIDE.md
├── QUICK_REFERENCE.md
├── launch_ubuntu.sh              ← Transfer to Ubuntu
└── ...
```

### On Ubuntu VM
```
/home/ubuntu/
├── launch_ubuntu.sh              ← Downloaded and run

/opt/swarmenterprise/             ← Project root
├── .env                          ← Auto-generated secrets
├── docker-compose.yml
├── docker-compose.prod.yml
├── backend/                      ← FastAPI code
├── agents/                       ← AI agents
├── scripts/                      ← Utilities
├── alembic/                      ← DB migrations
└── ...
```

---

## Environment Variables (Auto-Generated)

Located in: `/opt/swarmenterprise/.env`

```
# ===== Core Services =====
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@postgres:5432/docker
REDIS_URL=redis://redis:6379/0

# ===== Security =====
JWT_SECRET_KEY=<64-char hex>
SECRET_KEY=<64-char hex>
ENCRYPTION_KEY=<base64-32-byte>

# ===== Admin Credentials =====
ADMIN_EMAIL=admin@localhost
ADMIN_PASSWORD=AdminPassword123!

# ===== App Settings =====
ENV=development
BACKEND_PORT=8000
LOG_LEVEL=INFO
```

---

## Services & Ports

| Service | Port | Container | Protocol |
|---------|------|-----------|----------|
| **FastAPI** | 8000 | backend | HTTP |
| **PostgreSQL** | 5432 | postgres | TCP |
| **Redis** | 6379 | redis | TCP |
| **Flower** | 5555 | flower | HTTP (if running) |
| **Prometheus** | 9090 | prometheus | HTTP (if running) |
| **Grafana** | 3000 | grafana | HTTP (if running) |

---

## ✅ Success Indicators

After launch, you should see:

```
✓ docker compose ps shows 3+ running containers
✓ curl http://localhost:8000/health returns {"status": "ONLINE"}
✓ Browser loads http://192.168.1.100:8000/docs without errors
✓ Admin login works: admin@localhost / AdminPassword123!
✓ No errors in: docker compose logs backend
✓ Database has tables: docker compose exec postgres psql ... \dt
✓ Redis responds: docker compose exec redis redis-cli ping
```

---

## Troubleshooting Matrix

| Symptom | Root Cause | Solution |
|---------|-----------|----------|
| Can't SSH to Ubuntu | VM IP wrong | Check `Get-VMNetworkAdapter` |
| Connection refused | Backend down | `docker compose up -d backend` |
| Port 8000 in use | Other service | Change BACKEND_PORT in .env |
| Database error | Postgres not ready | Wait 10s, then retry |
| 502 Bad Gateway | Backend crashed | `docker compose logs backend` |
| Timeout on /health | Backend starting | Wait 30s, retry |
| Permission denied | Docker group | `sudo usermod -aG docker ubuntu` |

---

## Timeline Reference

| Phase | Task | Duration | On System |
|-------|------|----------|-----------|
| 1 | Enable Hyper-V | 2 min | Windows |
| 2 | Create VM | 5 min | Windows |
| 3 | Install Ubuntu | 10 min | Hyper-V |
| 4 | Boot to login | 5 min | Ubuntu |
| 5 | Run launch script | 15 min | Ubuntu |
| **Total** | **Full Setup** | **~40 min** | ✅ **DONE** |

---

## One-Liners for Common Tasks

### Windows PowerShell

```powershell
# Enable Hyper-V and restart
Enable-WindowsOptionalFeature -FeatureName Hyper-V -Online -All; Restart-Computer

# SSH to Ubuntu
ssh ubuntu@192.168.1.100

# Get VM IP
Get-VMNetworkAdapter -VMName swarmenterprise-vm | Select-Object IPAddresses

# Check API health
Invoke-RestMethod http://192.168.1.100:8000/health | ConvertTo-Json
```

### Ubuntu Bash

```bash
# SSH from Windows and run launch
ssh ubuntu@192.168.1.100 'cd /home/ubuntu && bash launch_ubuntu.sh'

# Check if running
docker compose ps

# View logs live
docker compose logs -f

# Restart backend
docker compose restart backend

# Full status
docker compose ps && curl localhost:8000/health
```

---

## Files You Created/Have

✅ **START_HERE.md** — 3-command quick start  
✅ **WINDOWS_UBUNTU_LAUNCH_GUIDE.md** — Complete walkthrough  
✅ **QUICK_REFERENCE.md** — Command cheatsheet  
✅ **launch_ubuntu.sh** — Automated setup script  
✅ **WINDOWS_TO_UBUNTU_COMPLETE_GUIDE.md** — Architecture & overview  
✅ **This file** — Visual reference & matrix  

---

## Next Steps

1. **Start Here:** Read `START_HERE.md`
2. **Setup Windows:** Run PowerShell commands
3. **Install Ubuntu:** Create VM, install Server
4. **Launch:** SSH and run `bash launch_ubuntu.sh`
5. **Verify:** Open browser to http://192.168.1.100:8000
6. **Manage:** Use commands from QUICK_REFERENCE.md

---

## Support Resources

- **Stuck?** → START_HERE.md
- **Need commands?** → QUICK_REFERENCE.md
- **Want details?** → WINDOWS_UBUNTU_LAUNCH_GUIDE.md
- **Architecture?** → This file
- **API?** → http://192.168.1.100:8000/docs

---

**Everything you need is ready. Let's launch!** 🚀
