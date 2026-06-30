# SwarmEnterprise v2 — Windows 11 + Ubuntu Hyper-V Quick Reference

## 🚀 Complete Launch in 3 Steps

### STEP 1: Windows 11 (5 minutes)

```powershell
# 1. Enable Hyper-V (PowerShell as Admin)
Enable-WindowsOptionalFeature -FeatureName Hyper-V -Online -All
Restart-Computer

# 2. Create Ubuntu VM using Hyper-V Manager or PowerShell script
# See WINDOWS_UBUNTU_LAUNCH_GUIDE.md for detailed instructions

# 3. Wait for Ubuntu to boot and get its IP
# (Open Hyper-V Manager → swarmenterprise-vm → Console tab)

# 4. SSH to Ubuntu (after Ubuntu is running)
ssh ubuntu@192.168.1.100  # Replace with actual VM IP
# (Enter password when prompted)
```

---

### STEP 2: Ubuntu VM (Copy & Paste This Entire Block)

```bash
# SSH into the Ubuntu VM first (from Windows PowerShell)
ssh ubuntu@192.168.1.100

# Then run these commands one at a time or paste the whole block:
cd /home/ubuntu && \
wget https://raw.githubusercontent.com/rwv-techsolutions/swarmenterprise-v2/main/launch_ubuntu.sh && \
chmod +x launch_ubuntu.sh && \
bash launch_ubuntu.sh

# This will take 10-15 minutes. Grab coffee ☕
```

---

### STEP 3: Verify from Windows (1 minute)

```powershell
# From Windows PowerShell (NOT in Ubuntu SSH session)

# Test health endpoint
Invoke-RestMethod -Uri "http://192.168.1.100:8000/health" | ConvertTo-Json

# Open in browser
Start-Process "http://192.168.1.100:8000/docs"

# Done! 🎉
```

---

## 📋 Command Reference by Environment

### From WINDOWS (PowerShell)

```powershell
# === VM Management ===
# Start VM
Start-VM -Name swarmenterprise-vm

# Stop VM
Stop-VM -Name swarmenterprise-vm

# Check VM status
Get-VM swarmenterprise-vm

# === SSH to Ubuntu ===
ssh ubuntu@192.168.1.100

# === File Transfer ===
# Copy FROM Windows TO Ubuntu VM
scp -r "C:\path\to\file" ubuntu@192.168.1.100:/home/ubuntu/

# Copy FROM Ubuntu VM TO Windows
scp -r "ubuntu@192.168.1.100:/home/ubuntu/file" "C:\local\path\"

# === Test API ===
Invoke-RestMethod -Uri "http://192.168.1.100:8000/health" -Method Get | ConvertTo-Json

# === Port Forwarding (if accessing from outside VM network) ===
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=192.168.1.100
```

### From UBUNTU VM (Bash)

```bash
# === Service Management ===
# Check all services
docker compose ps

# View logs (real-time)
docker compose logs -f backend

# Stop backend
docker compose stop backend

# Restart backend
docker compose restart backend

# Stop all services
docker compose down

# Start all services
docker compose up -d

# === Database Access ===
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d docker

# Seed data
python3 scripts/seed.py

# Run migrations
python3 scripts/run_alembic.py upgrade head

# === Testing ===
# Health check
curl http://localhost:8000/health

# List all API endpoints
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# === System Information ===
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU
top -n 1 | head -20

# Docker container info
docker stats --no-stream
```

---

## 🔑 Credentials & Secrets

After `bash launch_ubuntu.sh` completes:

```
Admin Email:        admin@localhost
Admin Password:     AdminPassword123!
Database User:      postgres
Database Password:  [in .env]
Redis:              redis://localhost:6379/0
```

**All secrets are stored in:**
```bash
/opt/swarmenterprise/.env
```

---

## 🌐 Access URLs (From Windows)

| Service | URL | Purpose |
|---------|-----|---------|
| **API** | http://192.168.1.100:8000 | Main API endpoint |
| **Swagger Docs** | http://192.168.1.100:8000/docs | Interactive API documentation |
| **Health Check** | http://192.168.1.100:8000/health | Service status |
| **Metrics** | http://192.168.1.100:8000/metrics | Prometheus metrics |
| **Flower** | http://192.168.1.100:5555 | Task monitor (if workers running) |

---

## 🛠️ Common Troubleshooting

### "Connection refused" from Windows

```bash
# Inside Ubuntu, check if backend is running:
docker compose ps

# If backend is down, start it:
docker compose up -d backend

# Check logs:
docker compose logs backend
```

### "Permission denied" when running Docker commands

```bash
# Inside Ubuntu:
sudo usermod -aG docker ubuntu
newgrp docker

# Then retry
docker ps
```

### "Port 8000 already in use"

```bash
# Inside Ubuntu:
sudo lsof -i :8000  # Find what's using it
sudo kill -9 <PID>  # Kill it

# Or change port in .env and restart:
nano .env  # Change BACKEND_PORT=8001
docker compose restart backend
```

### Database migration failed

```bash
# Inside Ubuntu:
# Check if Postgres is ready
docker compose exec postgres pg_isready -U postgres

# Wait a bit more if not ready, then retry:
python3 scripts/run_alembic.py upgrade head
```

### Can't SSH into Ubuntu from Windows

```powershell
# Verify Ubuntu VM is running
Get-VM swarmenterprise-vm

# Get the VM's IP address
Get-VMNetworkAdapter -VMName swarmenterprise-vm

# Try with password auth (simpler):
ssh -o PubkeyAuthentication=no ubuntu@<VM-IP>
```

---

## 📊 Service Status Checks

### Quick Health Check (From Ubuntu)

```bash
# All services in one command
echo "=== Container Status ===" && \
docker compose ps && \
echo "" && \
echo "=== Backend Health ===" && \
curl -s http://localhost:8000/health | jq . && \
echo "" && \
echo "=== Database ===" && \
docker compose exec postgres pg_isready -U postgres && \
echo "" && \
echo "=== Redis ===" && \
docker compose exec redis redis-cli ping
```

### Full Status Report (From Ubuntu)

```bash
# Save this as status.sh and run:
#!/bin/bash
echo "========== SWARMENTERPRISE STATUS =========="
echo ""
echo "Docker Containers:"
docker compose ps
echo ""
echo "Backend Health:"
curl -s http://localhost:8000/health | jq .
echo ""
echo "Database Tables:"
docker compose exec postgres psql -U postgres -d docker -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
echo ""
echo "Redis Info:"
docker compose exec redis redis-cli info keyspace
echo ""
echo "Disk Usage:"
df -h | grep -E "^Filesystem|/$"
echo ""
echo "Memory Usage:"
free -h
echo ""
echo "========== END STATUS =========="
```

---

## 🚀 Next Steps After Launch

### 1. Configure for Production
```bash
# Inside Ubuntu VM
cd /opt/swarmenterprise

# Edit .env for production
nano .env

# Change:
# ENV=development  →  ENV=production
# DEPLOY_PROFILE=local  →  DEPLOY_PROFILE=production-realms2riches
# STRIPE_TEST_MODE=TRUE  →  STRIPE_TEST_MODE=FALSE
# DRY_RUN_MODE=true  →  DRY_RUN_MODE=false

# Restart services
docker compose down
docker compose up -d
```

### 2. Set Up SSL/TLS (Optional)
```bash
# Inside Ubuntu VM, start Caddy reverse proxy
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile proxy up -d caddy

# This auto-provisions Let's Encrypt certificates
```

### 3. Scale Workers (For Task Processing)
```bash
# Inside Ubuntu VM
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile workers up -d worker beat flower

# Scale to 3 workers
docker compose up -d --scale worker=3
```

### 4. Enable Monitoring
```bash
# Inside Ubuntu VM
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d prometheus grafana

# Access Grafana at http://192.168.1.100:3000
# Default login: admin / admin
```

---

## 📝 Files You Need

### On Windows
- Download: `launch_ubuntu.sh` from SwarmEnterprise repo
- Ubuntu 22.04 ISO: https://releases.ubuntu.com/jammy/

### On Ubuntu VM (After Launch)
- `.env` — Environment configuration (auto-generated)
- `docker-compose.yml` — Service definitions
- `docker-compose.prod.yml` — Production hardening
- `/opt/swarmenterprise/` — Full repository

---

## ⏱️ Timeline

| Step | Duration | What Happens |
|------|----------|---|
| 1. Enable Hyper-V on Windows | 2 min + restart | Windows feature enabled |
| 2. Create Ubuntu VM | 5 min | VM provisioned (8GB, 80GB disk) |
| 3. Install Ubuntu | 10 min | OS installed, boots to login |
| 4. Run launch_ubuntu.sh | 10–15 min | Docker, Python, services installed & running |
| **Total** | **~45 min** | **SwarmEnterprise live!** 🎉 |

---

## 🎯 Success Checklist

After everything is running:

- [ ] Windows can SSH to Ubuntu VM
- [ ] `docker compose ps` shows 3+ containers (postgres, redis, backend)
- [ ] `curl http://192.168.1.100:8000/health` returns ONLINE
- [ ] Browser loads http://192.168.1.100:8000/docs without errors
- [ ] Admin credentials work (admin@localhost / AdminPassword123!)
- [ ] `.env` file has strong secrets (64-char keys)
- [ ] All services show in `docker stats` with healthy status
- [ ] Logs contain no errors: `docker compose logs | grep -i error`

---

## 📞 Support

- **Ubuntu SSH issues:** Check Hyper-V Manager → VM console
- **Docker issues:** `docker logs` and `docker compose logs`
- **Database issues:** `docker compose exec postgres psql -U postgres`
- **API issues:** Check http://192.168.1.100:8000/health

---

**Ready to launch? Start with Step 1!** 🚀
