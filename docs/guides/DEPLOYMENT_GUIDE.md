# SwarmEnterprise v2 - Self-Hosted Deployment Guide

Complete step-by-step guide to deploy SwarmEnterprise v2 on your Windows Server 2025 VM with WSL2 and Ollama on your laptop.

**Total Cost:** $0/month (only electricity)  
**Time to Deploy:** ~2 hours  
**Difficulty:** Intermediate

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Laptop Setup (Ollama)](#laptop-setup-ollama)
3. [Windows Server 2025 Setup](#windows-server-2025-setup)
4. [WSL2 Ubuntu Setup](#wsl2-ubuntu-setup)
5. [Docker Stack Deployment](#docker-stack-deployment)
6. [DNS Configuration](#dns-configuration)
7. [SSL Certificates](#ssl-certificates)
8. [Initial Configuration](#initial-configuration)
9. [Monitoring Setup](#monitoring-setup)
10. [Backup Strategy](#backup-strategy)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements

**Laptop (Ollama Server):**
- CPU: 4+ cores
- RAM: 16GB+ (32GB recommended)
- Storage: 50GB+ free space
- GPU: Optional but recommended (NVIDIA with CUDA)
- Network: Stable connection to Windows Server VM

**Windows Server 2025 VM:**
- CPU: 8+ cores (16 recommended)
- RAM: 32GB+ (64GB recommended)
- Storage: 500GB+ SSD
- Network: Static IP address
- Hyper-V enabled

### Software Requirements

- Windows Server 2025 (licensed or evaluation)
- Ubuntu 22.04 LTS (via WSL2)
- Docker & Docker Compose
- Git
- Domain names (realms2riches.com, realms2riches.tech)

---

## Laptop Setup (Ollama)

### Step 1: Install Ollama

**Windows:**
```powershell
# Download and install from https://ollama.com/download
# Or use winget
winget install Ollama.Ollama
```

**macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Configure Ollama for Network Access

**Windows (PowerShell as Admin):**
```powershell
# Set environment variables
[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'Machine')
[System.Environment]::SetEnvironmentVariable('OLLAMA_ORIGINS', '*', 'Machine')

# Restart Ollama service
Restart-Service Ollama
```

**Linux/macOS:**
```bash
# Edit systemd service (Linux)
sudo systemctl edit ollama.service

# Add these lines:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=*"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Step 3: Pull Required Models

```bash
# Pull models (this will take time, models are large)
ollama pull llama3          # 4.7GB - General purpose
ollama pull codellama       # 3.8GB - Code generation
ollama pull mistral         # 4.1GB - Alternative general model

# Verify models
ollama list
```

### Step 4: Test Ollama

```bash
# Test generation
ollama run llama3 "Hello, how are you?"

# Test from network (from another machine)
curl http://YOUR_LAPTOP_IP:11434/api/generate -d '{
  "model": "llama3",
  "prompt": "Why is the sky blue?"
}'
```

### Step 5: Configure Firewall

**Windows:**
```powershell
# Allow Ollama port
New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

**Linux:**
```bash
sudo ufw allow 11434/tcp
```

### Step 6: Get Laptop IP Address

```bash
# Windows
ipconfig

# Linux/macOS
ip addr show  # or ifconfig
```

**Note this IP address** - you'll need it for the backend configuration (e.g., `192.168.1.100`)

---

## Windows Server 2025 Setup

### Step 1: Install Windows Server 2025

1. Install Windows Server 2025 (Standard or Datacenter)
2. Set static IP address
3. Configure hostname: `dc01.corp.realms2riches.com`
4. Install all Windows updates

### Step 2: Promote to Domain Controller

```powershell
# Install AD DS role
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

# Promote to Domain Controller
Install-ADDSForest `
    -DomainName "corp.realms2riches.com" `
    -DomainNetbiosName "REALMS2RICHES" `
    -DomainMode "WinThreshold" `
    -ForestMode "WinThreshold" `
    -InstallDns `
    -SafeModeAdministratorPassword (ConvertTo-SecureString "YourSecurePassword123!" -AsPlainText -Force) `
    -Force

# Server will restart
```

### Step 3: Configure DNS Zones

```powershell
# After restart, configure DNS zones
Add-DnsServerPrimaryZone -Name "realms2riches.com" -ZoneFile "realms2riches.com.dns"
Add-DnsServerPrimaryZone -Name "realms2riches.tech" -ZoneFile "realms2riches.tech.dns"

# Add DNS records (replace with your WSL2 IP)
$WSL_IP = "172.20.0.1"  # Get this from WSL2 later

Add-DnsServerResourceRecordA -Name "@" -ZoneName "realms2riches.com" -IPv4Address $WSL_IP
Add-DnsServerResourceRecordA -Name "www" -ZoneName "realms2riches.com" -IPv4Address $WSL_IP
Add-DnsServerResourceRecordA -Name "api" -ZoneName "realms2riches.com" -IPv4Address $WSL_IP
Add-DnsServerResourceRecordA -Name "corp" -ZoneName "realms2riches.com" -IPv4Address $WSL_IP
Add-DnsServerResourceRecordA -Name "minio" -ZoneName "realms2riches.com" -IPv4Address $WSL_IP
Add-DnsServerResourceRecordA -Name "grafana" -ZoneName "realms2riches.com" -IPv4Address $WSL_IP

# Wildcard for tenants
Add-DnsServerResourceRecordA -Name "*" -ZoneName "realms2riches.tech" -IPv4Address $WSL_IP
```

### Step 4: Enable Hyper-V

```powershell
# Install Hyper-V
Install-WindowsFeature -Name Hyper-V -IncludeManagementTools -Restart

# After restart, configure Hyper-V
New-VMSwitch -Name "External" -NetAdapterName "Ethernet" -AllowManagementOS $true
```

### Step 5: Install WSL2

```powershell
# Enable WSL
wsl --install

# Set WSL2 as default
wsl --set-default-version 2

# Install Ubuntu 22.04
wsl --install -d Ubuntu-22.04

# Restart if needed
```

---

## WSL2 Ubuntu Setup

### Step 1: Initial Ubuntu Configuration

```bash
# Launch WSL2
wsl -d Ubuntu-22.04

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release
```

### Step 2: Install Docker

```bash
# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify
docker --version
docker compose version
```

### Step 3: Configure Docker

```bash
# Create Docker daemon config
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

# Restart Docker
sudo systemctl restart docker
```

### Step 4: Get WSL2 IP Address

```bash
# Get WSL2 IP
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1

# Note this IP - you'll need it for DNS configuration
```

---

## Docker Stack Deployment

### Step 1: Clone Repository

```bash
# Create project directory
mkdir -p ~/projects
cd ~/projects

# Clone repository
git clone https://github.com/yourusername/SwarmEnterprise-v2.git
cd SwarmEnterprise-v2
```

### Step 2: Create Environment File

```bash
# Copy example environment file
cp .env.example .env.production

# Edit environment file
nano .env.production
```

**`.env.production` contents:**
```bash
# Database
DB_PASSWORD=your-super-secure-database-password-here

# MinIO (S3)
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-super-secure-minio-password-here

# JWT
JWT_SECRET=your-super-secure-jwt-secret-key-here-min-32-chars

# Ollama (your laptop IP)
OLLAMA_URL=http://192.168.1.100:11434  # REPLACE WITH YOUR LAPTOP IP

# Grafana
GRAFANA_PASSWORD=your-grafana-admin-password

# Application
APP_ENV=production
DEBUG=false
```

**Generate secure passwords:**
```bash
# Generate random passwords
openssl rand -base64 32  # For DB_PASSWORD
openssl rand -base64 32  # For MINIO_SECRET_KEY
openssl rand -base64 48  # For JWT_SECRET
openssl rand -base64 16  # For GRAFANA_PASSWORD
```

### Step 3: Create Required Directories

```bash
# Create directories
mkdir -p output logs monitoring/grafana/dashboards monitoring/grafana/datasources

# Set permissions
chmod -R 755 output logs monitoring
```

### Step 4: Copy Caddyfile

```bash
# Copy self-hosted Caddyfile
cp deploy/Caddyfile.self-hosted deploy/Caddyfile

# Edit if needed
nano deploy/Caddyfile
```

### Step 5: Build and Start Services

```bash
# Build images
docker compose -f docker-compose.production-self-hosted.yml build

# Start services
docker compose -f docker-compose.production-self-hosted.yml up -d

# Check status
docker compose -f docker-compose.production-self-hosted.yml ps

# View logs
docker compose -f docker-compose.production-self-hosted.yml logs -f
```

### Step 6: Verify Services

```bash
# Check all containers are running
docker ps

# Test backend health
curl http://localhost:8000/health

# Test MinIO
curl http://localhost:9000/minio/health/live

# Test Redis
docker exec swarm_redis redis-cli ping

# Test PostgreSQL
docker exec swarm_postgres pg_isready -U swarm
```

---

### Step 7: Smoke Test

After all containers are running and DNS is resolvable, run the full smoke test
to validate every critical endpoint end-to-end.

#### Quick validation (bash)

```bash
# Make the script executable (once)
chmod +x scripts/smoke_test.sh

# Test against a live deployment
./scripts/smoke_test.sh https://yourdomain.com

# Test against a local stack
./scripts/smoke_test.sh http://localhost:8000

# Verbose output (prints full response bodies)
./scripts/smoke_test.sh https://yourdomain.com --verbose
```

The script exits **0** if all checks pass and **1** if any check fails — suitable
for blocking a CI/CD pipeline stage.

#### Detailed assertion output (Python)

For richer output with per-assertion detail, use `scripts/smoke_api.py`:

```bash
# In-process test (no running server required)
python scripts/smoke_api.py

# Against a live deployment
python scripts/smoke_api.py --base-url https://yourdomain.com

# Verbose — prints response bodies
python scripts/smoke_api.py --base-url https://yourdomain.com --verbose
```

See [`scripts/smoke_api.py`](../../scripts/smoke_api.py) for the full list of
assertions and to add custom checks.

#### Expected passing conditions

All of the following must be true for the smoke test to report **PASS**:

| # | Endpoint | Method | Expected | Notes |
|---|----------|--------|----------|-------|
| 1 | `/health` | GET | `200` | Response body must contain `"status": "ONLINE"` |
| 2 | `/health` body | — | `"ONLINE"` | `status` field assertion |
| 3 | `/metrics` | GET | `200` | Prometheus metrics text |
| 4 | `/docs` | GET | `200` | Swagger UI is served |
| 5 | `/api/auth/register` | POST | `201` | New smoke-test user created |
| 6 | `/api/auth/register` body | — | `access_token` present | JWT issued on registration |
| 7 | `/api/auth/login` | POST | `200` | Login succeeds for registered user |
| 8 | `/api/auth/login` body | — | `access_token` present | JWT returned |
| 9 | `/api/auth/verify` | GET | `200` | Token accepted by auth middleware |
| 10 | `/api/companies/` | GET | `200` | Authenticated list request succeeds |
| 11 | `/api/companies/` (no token) | GET | `401`/`403` | Auth guard is active |
| 12 | `/api/stripe/create-checkout-session` | GET | `405` | Route is mounted (POST-only endpoint) |
| 13 | HTTPS TLS check | HEAD | `200` | Only when `BASE_URL` is `https://` |

> **Note on `/api/payments/plans`:** The payments router is mounted under
> `/api/stripe`. Use `/api/stripe/create-checkout-session` (POST) to test
> payment-related routing in your integration suite.

#### Integrating into CI/CD

```yaml
# Example GitHub Actions step
- name: Smoke test staging
  run: ./scripts/smoke_test.sh ${{ secrets.STAGING_URL }}
```

---

## DNS Configuration

### Option 1: Local DNS (Development)

Edit your hosts file to test locally:

**Windows (C:\Windows\System32\drivers\etc\hosts):**
```
172.20.0.1  realms2riches.com
172.20.0.1  www.realms2riches.com
172.20.0.1  api.realms2riches.com
172.20.0.1  corp.realms2riches.com
172.20.0.1  minio.realms2riches.com
172.20.0.1  grafana.realms2riches.com
```

### Option 2: Public DNS (Production)

Configure your domain registrar to point to your public IP:

1. Get your public IP: `curl ifconfig.me`
2. Configure A records at your registrar:
   - `realms2riches.com` → Your Public IP
   - `*.realms2riches.com` → Your Public IP
   - `*.realms2riches.tech` → Your Public IP

3. Configure port forwarding on your router:
   - Port 80 → WSL2 IP:80
   - Port 443 → WSL2 IP:443

---

## SSL Certificates

Caddy automatically handles SSL certificates via Let's Encrypt!

### Automatic SSL (Recommended)

Caddy will automatically:
1. Request certificates from Let's Encrypt
2. Renew certificates before expiry
3. Handle HTTPS redirects

**Requirements:**
- Domain must resolve to your server
- Ports 80 and 443 must be accessible from internet
- Valid email in Caddyfile

### Manual SSL (Optional)

If you need custom certificates:

```bash
# Place certificates in deploy/certs/
mkdir -p deploy/certs

# Update Caddyfile
nano deploy/Caddyfile

# Add TLS directive
realms2riches.com {
    tls /etc/caddy/certs/cert.pem /etc/caddy/certs/key.pem
    # ... rest of config
}
```

---

## Initial Configuration

### Step 1: Initialize Database

```bash
# Run database migrations
docker compose -f docker-compose.production-self-hosted.yml exec backend python -m alembic upgrade head

# Or initialize from scratch
docker compose -f docker-compose.production-self-hosted.yml exec backend python -c "
from backend.db.init_db import init_db
init_db()
"
```

### Step 2: Create Admin User

```bash
# Create admin user
docker compose -f docker-compose.production-self-hosted.yml exec backend python -c "
from backend.auth.user_service import UserService
from backend.auth.permissions import Role

service = UserService()
admin = service.create_user({
    'email': 'admin@realms2riches.com',
    'password': 'ChangeMe123!',
    'full_name': 'System Administrator',
    'role': Role.SUPERADMIN
})
print(f'Admin user created: {admin.email}')
"
```

### Step 3: Test Ollama Connection

```bash
# Test Ollama from backend
docker compose -f docker-compose.production-self-hosted.yml exec backend python -c "
import asyncio
from backend.llm.ollama_client import OllamaClient

async def test():
    client = OllamaClient()
    healthy = await client.health_check()
    print(f'Ollama healthy: {healthy}')
    
    if healthy:
        models = await client.list_models()
        print(f'Available models: {[m[\"name\"] for m in models]}')
    
    await client.close()

asyncio.run(test())
"
```

### Step 4: Configure MinIO Buckets

```bash
# MinIO should auto-create buckets via minio_init container
# Verify buckets exist
docker compose -f docker-compose.production-self-hosted.yml exec minio mc ls myminio/

# If needed, create manually
docker compose -f docker-compose.production-self-hosted.yml exec minio mc mb myminio/swarm-companies
```

---

## Database Migrations

SwarmEnterprise v2 uses **Alembic** as its database migration framework, integrated with the
SQLAlchemy models defined in `backend/db/models.py`.

### Before starting the application — always run migrations first

```bash
# Apply all pending migrations to bring the database to the latest schema
make db-upgrade
```

This is equivalent to running `alembic upgrade head` and must be executed:
- On **initial deployment** before any service accepts traffic
- After every `git pull` that includes model changes
- As part of any automated CI/CD deployment pipeline

### Creating a new migration after changing models

When you add, rename, or remove columns/tables in `backend/db/models.py`, generate a
migration script automatically:

```bash
make db-migrate MSG="add subscription_plan to users"
```

This runs `alembic revision --autogenerate -m "<MSG>"` and writes a new versioned file into
`alembic/versions/`. Always review the generated script before committing — autogenerate
cannot detect column renames or certain constraint changes.

### Rolling back the last migration

```bash
make db-downgrade
```

Reverts exactly one migration step (`alembic downgrade -1`). Run it again to step back further.

### Running migrations inside Docker

```bash
# Apply migrations inside the running backend container
docker compose exec backend alembic upgrade head

# Generate a migration inside the container (source mounted as a volume)
docker compose exec backend alembic revision --autogenerate -m "describe change"
```

### Environment variable requirement

Alembic reads the database connection string exclusively from the `DATABASE_URL` environment
variable. Ensure it is set before running any `alembic` or `make db-*` command:

```bash
export DATABASE_URL="postgresql://swarm:password@localhost:5432/swarmdb"
make db-upgrade
```

### Migration files

All migration scripts are stored in `alembic/versions/` and **must be committed** to version
control alongside the model changes that triggered them.

---

## Monitoring Setup

### Step 1: Access Grafana

1. Open browser: `https://grafana.realms2riches.com`
2. Login with admin credentials from `.env.production`
3. Default username: `admin`

### Step 2: Configure Datasources

Grafana should auto-configure datasources, but verify:

1. Go to Configuration → Data Sources
2. Verify Prometheus is configured: `http://prometheus:9090`
3. Verify Loki is configured: `http://loki:3100`

### Step 3: Import Dashboards

```bash
# Copy dashboard configs
cp monitoring/grafana/dashboards/*.json /path/to/grafana/dashboards/

# Or import via UI:
# Dashboards → Import → Upload JSON
```

### Step 4: Set Up Alerts

1. Go to Alerting → Alert rules
2. Create alerts for:
   - High CPU usage
   - High memory usage
   - Service down
   - Disk space low

---

## Backup Strategy

### Automated Backup Script

```bash
# Create backup script
cat > ~/backup-swarm.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/mnt/backups/swarm"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec swarm_postgres pg_dump -U swarm swarm | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup MinIO data
docker exec swarm_minio mc mirror /data $BACKUP_DIR/minio_$DATE/

# Backup Redis
docker exec swarm_redis redis-cli --rdb /data/dump.rdb
docker cp swarm_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup environment and configs
cp .env.production $BACKUP_DIR/env_$DATE
cp -r deploy $BACKUP_DIR/deploy_$DATE/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x ~/backup-swarm.sh
```

### Schedule Backups

```bash
# Add to crontab
crontab -e

# Add this line (daily at 2 AM)
0 2 * * * /home/yourusername/backup-swarm.sh >> /var/log/swarm-backup.log 2>&1
```

---

## Troubleshooting

### Ollama Connection Issues

```bash
# Test from WSL2
curl http://YOUR_LAPTOP_IP:11434/api/tags

# Check firewall on laptop
# Windows: Check Windows Firewall
# Linux: sudo ufw status

# Verify Ollama is listening on all interfaces
# Should show 0.0.0.0:11434, not 127.0.0.1:11434
netstat -an | grep 11434
```

### Docker Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.production-self-hosted.yml logs backend

# Check disk space
df -h

# Check memory
free -h

# Restart specific service
docker compose -f docker-compose.production-self-hosted.yml restart backend
```

### SSL Certificate Issues

```bash
# Check Caddy logs
docker compose -f docker-compose.production-self-hosted.yml logs caddy

# Verify DNS is resolving correctly
nslookup realms2riches.com

# Test Let's Encrypt connectivity
curl https://acme-v02.api.letsencrypt.org/directory
```

### Database Connection Issues

```bash
# Check PostgreSQL logs
docker compose -f docker-compose.production-self-hosted.yml logs postgres

# Test connection
docker exec swarm_postgres psql -U swarm -d swarm -c "SELECT 1;"

# Reset database (CAUTION: destroys data)
docker compose -f docker-compose.production-self-hosted.yml down -v
docker compose -f docker-compose.production-self-hosted.yml up -d
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check system resources
htop

# Optimize Docker
docker system prune -a

# Increase Docker resources (if needed)
# Edit /etc/docker/daemon.json
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Check service health: `docker compose ps`
- Review logs: `docker compose logs --tail=100`
- Monitor disk space: `df -h`

**Weekly:**
- Update Docker images: `docker compose pull`
- Review Grafana dashboards
- Check backup integrity

**Monthly:**
- Update system packages: `sudo apt update && sudo apt upgrade`
- Review and rotate logs
- Update Ollama models: `ollama pull llama3`
- Security audit

### Updating the Application

```bash
# Pull latest code
cd ~/projects/SwarmEnterprise-v2
git pull

# Rebuild and restart
docker compose -f docker-compose.production-self-hosted.yml build
docker compose -f docker-compose.production-self-hosted.yml up -d

# Run migrations if needed
docker compose -f docker-compose.production-self-hosted.yml exec backend python -m alembic upgrade head
```

---

## Cost Summary

| Item | Monthly Cost |
|------|--------------|
| Software licenses | $0 |
| Cloud services | $0 |
| Domain registration | ~$1 |
| SSL certificates | $0 (Let's Encrypt) |
| Electricity (estimated) | $20-50 |
| **TOTAL** | **$21-51** |

**Compared to cloud:** Saves $500-1000/month (95% reduction)

---

## Next Steps

1. ✅ Deploy infrastructure
2. ✅ Configure monitoring
3. ✅ Set up backups
4. 🔄 Test company generation
5. 🔄 Deploy first tenant
6. 🔄 Configure CI/CD
7. 🔄 Set up agent swarm
8. 🔄 Go live!

---

## Support

For issues or questions:
- Check logs: `docker compose logs`
- Review documentation: `README.md`
- Check GitHub issues
- Contact: admin@realms2riches.com

---

**Congratulations!** You now have a fully self-hosted, zero-cost SwarmEnterprise v2 deployment! 🎉