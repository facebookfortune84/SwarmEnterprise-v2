# SwarmEnterprise v2 - Quick Start Guide

Get up and running in under 30 minutes!

---

## 🚀 Prerequisites

### Hardware
- **Laptop:** 16GB+ RAM, 4+ CPU cores (for Ollama)
- **Server:** Windows Server 2025 VM with 32GB+ RAM, 8+ CPU cores

### Software
- Windows Server 2025
- WSL2 Ubuntu 22.04
- Docker & Docker Compose
- Git

---

## ⚡ 5-Minute Setup

### Step 1: Ollama on Laptop (2 minutes)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Configure for network access
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_ORIGINS=*

# Start server
ollama serve &

# Pull models (runs in background)
ollama pull llama3 &
ollama pull codellama &

# Get your laptop IP
ip addr show | grep "inet " | grep -v 127.0.0.1
# Note this IP (e.g., 192.168.1.100)
```

### Step 2: Windows Server Setup (5 minutes)

```powershell
# Enable Hyper-V
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Install WSL2
wsl --install -d Ubuntu-22.04

# Restart if needed
Restart-Computer
```

### Step 3: WSL2 Docker Setup (3 minutes)

```bash
# In WSL2 Ubuntu
sudo apt update
sudo apt install -y docker.io docker-compose git

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker
```

### Step 4: Deploy SwarmEnterprise (5 minutes)

```bash
# Clone repository
cd ~
git clone https://github.com/yourusername/SwarmEnterprise-v2.git
cd SwarmEnterprise-v2

# Create environment file
cp .env.example .env.production

# Edit with your laptop IP
nano .env.production
# Set: OLLAMA_URL=http://192.168.1.100:11434

# Generate secure passwords
openssl rand -base64 32  # For DB_PASSWORD
openssl rand -base64 32  # For MINIO_SECRET_KEY
openssl rand -base64 48  # For JWT_SECRET

# Add passwords to .env.production

# Deploy!
docker-compose -f docker-compose.production-self-hosted.yml up -d

# Check status
docker-compose ps
```

### Step 5: Verify (2 minutes)

```bash
# Check all services are running
docker-compose -f docker-compose.production-self-hosted.yml ps

# Test backend
curl http://localhost:8000/health

# Test Ollama connection
docker-compose exec backend python -c "
import asyncio
from backend.llm.ollama_client import OllamaClient

async def test():
    client = OllamaClient()
    healthy = await client.health_check()
    print(f'Ollama: {\"✅\" if healthy else \"❌\"}')
    await client.close()

asyncio.run(test())
"
```

---

## 🎯 First Steps

### 1. Access Services

```bash
# Grafana (monitoring)
https://grafana.realms2riches.com
# Login: admin / (password from .env.production)

# MinIO (storage)
https://minio.realms2riches.com
# Login: minioadmin / (password from .env.production)

# API
https://api.realms2riches.com/docs
# Interactive API documentation

# Main site
https://realms2riches.com
```

### 2. Create Admin User

```bash
docker-compose exec backend python -c "
from backend.auth.user_service import UserService
from backend.auth.permissions import Role

service = UserService()
admin = service.create_user({
    'email': 'admin@realms2riches.com',
    'password': 'ChangeMe123!',
    'full_name': 'System Administrator',
    'role': Role.SUPERADMIN
})
print(f'Admin created: {admin.email}')
"
```

### 3. Generate Your First Company

```bash
# Via API
curl -X POST https://api.realms2riches.com/api/companies/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Company",
    "description": "A simple todo app with React and FastAPI",
    "tech_stack": "fastapi-react-postgres"
  }'

# Check status
curl https://api.realms2riches.com/api/companies/{id}/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Download when ready
curl https://api.realms2riches.com/api/companies/{id}/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o company.zip
```

### 4. Deploy to VM

```bash
# Create deployment
curl -X POST https://api.realms2riches.com/api/deployments \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "comp-123",
    "tenant_name": "my-company",
    "subdomain": "mycompany",
    "memory_mb": 4096,
    "cpu_cores": 2,
    "disk_size_gb": 50
  }'

# Check deployment status
curl https://api.realms2riches.com/api/deployments/{id} \
  -H "Authorization: Bearer YOUR_TOKEN"

# Access your deployed company
https://mycompany.realms2riches.tech
```

---

## 🔧 Common Commands

### Docker Management

```bash
# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Stop all
docker-compose down

# Start all
docker-compose up -d

# Rebuild
docker-compose build backend
docker-compose up -d backend
```

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U swarm -d swarm

# Backup database
docker-compose exec postgres pg_dump -U swarm swarm > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U swarm swarm
```

### Monitoring

```bash
# View Prometheus metrics
curl http://localhost:9090/metrics

# View backend metrics
curl http://localhost:8000/metrics

# Check service health
curl http://localhost:8000/health
```

### VM Management

```powershell
# List VMs (on Windows Server)
Get-VM

# Start VM
Start-VM -Name "tenant-mycompany"

# Stop VM
Stop-VM -Name "tenant-mycompany"

# Get VM status
Get-VM -Name "tenant-mycompany" | Select Name, State, Uptime
```

---

## 🐛 Troubleshooting

### Ollama Not Accessible

```bash
# Check Ollama is running
curl http://YOUR_LAPTOP_IP:11434/api/tags

# Check firewall
# Windows: Allow port 11434 in Windows Firewall
# Linux: sudo ufw allow 11434/tcp

# Verify OLLAMA_HOST
echo $OLLAMA_HOST  # Should be 0.0.0.0:11434
```

### Docker Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Check disk space
df -h

# Check memory
free -h

# Restart Docker
sudo systemctl restart docker
```

### Can't Access Services

```bash
# Check Caddy is running
docker-compose ps caddy

# Check Caddy logs
docker-compose logs caddy

# Verify DNS
nslookup api.realms2riches.com

# Check ports
netstat -tulpn | grep -E '80|443'
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres pg_isready -U swarm

# Check logs
docker-compose logs postgres
```

---

## 📚 Next Steps

1. **Read Full Documentation**
   - `DEPLOYMENT_GUIDE.md` - Complete deployment guide
   - `SELF_HOSTED_ARCHITECTURE.md` - Architecture details
   - `PROJECT_STATUS.md` - Current project status

2. **Explore API**
   - Visit https://api.realms2riches.com/docs
   - Try the interactive API documentation
   - Generate your first company

3. **Set Up Monitoring**
   - Access Grafana dashboards
   - Configure alerts
   - Review metrics

4. **Customize**
   - Add your own templates
   - Configure agents
   - Adjust resource limits

---

## 💡 Tips

### Performance Optimization

```bash
# Increase Docker resources (if needed)
# Edit /etc/docker/daemon.json
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}

# Restart Docker
sudo systemctl restart docker
```

### Security Hardening

```bash
# Enable firewall
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Disable root SSH
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
sudo systemctl restart sshd
```

### Backup Strategy

```bash
# Create backup script
cat > ~/backup-swarm.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/mnt/backups/swarm"

mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U swarm swarm | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup MinIO
docker-compose exec -T minio mc mirror /data $BACKUP_DIR/minio_$DATE/

# Backup configs
cp .env.production $BACKUP_DIR/env_$DATE

echo "Backup completed: $DATE"
EOF

chmod +x ~/backup-swarm.sh

# Schedule daily backups
crontab -e
# Add: 0 2 * * * /home/yourusername/backup-swarm.sh
```

---

## 🎉 Success!

You now have a fully functional, self-hosted AI digital factory!

**What you can do:**
- ✅ Generate companies with AI
- ✅ Deploy to VMs automatically
- ✅ Monitor everything in real-time
- ✅ Scale infinitely on your hardware
- ✅ Pay only for electricity

**Cost:** $21-51/month (vs $500-1000/month cloud)  
**Savings:** 95%+

---

## 🆘 Need Help?

- **Documentation:** Check `DEPLOYMENT_GUIDE.md`
- **Issues:** Check `PROJECT_STATUS.md`
- **Architecture:** Check `SELF_HOSTED_ARCHITECTURE.md`
- **GitHub:** https://github.com/yourusername/SwarmEnterprise-v2

---

**Happy Building!** 🚀