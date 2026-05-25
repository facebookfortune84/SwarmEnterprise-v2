# SwarmEnterprise v2 - Self-Hosted Architecture

## Overview
Complete self-hosted, zero-cost architecture using only free and open-source software.

**Total Cost:** $0/month (only electricity)  
**Infrastructure:** Single Windows Server 2025 VM with WSL2  
**Domain Controller:** corp.realms2riches.com  
**LLM Engine:** Ollama (running on laptop)

---

## Infrastructure Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR LAPTOP                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Ollama Server (http://192.168.1.X:11434)                  │ │
│  │  - Model: llama3, codellama, mistral, etc.                 │ │
│  │  - Accessible via local network                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP
┌─────────────────────────────────────────────────────────────────┐
│              WINDOWS SERVER 2025 VM (Hyper-V Host)              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Domain Controller: corp.realms2riches.com                 │ │
│  │  - Active Directory                                        │ │
│  │  - DNS Server                                              │ │
│  │  - IIS (optional)                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  WSL2 Ubuntu (Primary Application Host)                    │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  Docker Compose Stack                                │  │ │
│  │  │  ├── FastAPI Backend (port 8000)                     │  │ │
│  │  │  ├── PostgreSQL (port 5432)                          │  │ │
│  │  │  ├── Redis (port 6379)                               │  │ │
│  │  │  ├── MinIO (S3-compatible, ports 9000/9001)          │  │ │
│  │  │  ├── Caddy (reverse proxy, ports 80/443)            │  │ │
│  │  │  └── ChromaDB (vector store, port 8001)             │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  Agent Swarm (Python processes)                      │  │ │
│  │  │  - Strategic Board (12 managers)                     │  │ │
│  │  │  - Worker Pairs (executor + critic)                  │  │ │
│  │  │  - DevOps Agents                                     │  │ │
│  │  │  - Self-Healing Agents                               │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Nested VMs (Hyper-V) - Generated Companies                │ │
│  │  ├── tenant-1.realms2riches.tech                           │ │
│  │  ├── tenant-2.realms2riches.tech                           │ │
│  │  └── tenant-N.realms2riches.tech                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Free & Open Source Stack

### Core Services (All Free)

| Service | Purpose | License | Cost |
|---------|---------|---------|------|
| **Ollama** | LLM inference engine | MIT | $0 |
| **PostgreSQL** | Primary database | PostgreSQL | $0 |
| **Redis** | Cache & queue | BSD | $0 |
| **MinIO** | S3-compatible storage | AGPL v3 | $0 |
| **Caddy** | Reverse proxy & SSL | Apache 2.0 | $0 |
| **ChromaDB** | Vector database | Apache 2.0 | $0 |
| **Docker** | Containerization | Apache 2.0 | $0 |
| **Ubuntu** | OS (WSL2) | GPL | $0 |
| **Python** | Runtime | PSF | $0 |
| **FastAPI** | Web framework | MIT | $0 |

### Replaced Paid Services

| Paid Service | Free Alternative | Savings |
|--------------|------------------|---------|
| OpenAI API | Ollama (local) | ~$100-500/mo |
| AWS S3 | MinIO (self-hosted) | ~$20-100/mo |
| Stripe | Manual/crypto payments | ~3% + $0.30/tx |
| Heroku/Vercel | Self-hosted | ~$25-100/mo |
| MongoDB Atlas | PostgreSQL | ~$57/mo |
| Redis Cloud | Redis (self-hosted) | ~$5-50/mo |
| **TOTAL SAVINGS** | | **~$200-800/mo** |

---

## Detailed Component Configuration

### 1. Ollama Setup (Laptop)

**Installation:**
```bash
# On your laptop
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server (accessible on network)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Pull models
ollama pull llama3
ollama pull codellama
ollama pull mistral
```

**Configuration:**
```bash
# Make Ollama accessible from network
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_ORIGINS=*
```

**Environment Variable for Backend:**
```bash
OLLAMA_URL=http://192.168.1.X:11434  # Your laptop's IP
```

---

### 2. Windows Server 2025 Setup

**Domain Controller Configuration:**
```powershell
# Install AD DS
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

# Promote to Domain Controller
Install-ADDSForest `
    -DomainName "corp.realms2riches.com" `
    -DomainNetbiosName "REALMS2RICHES" `
    -InstallDns

# Configure DNS for subdomains
Add-DnsServerPrimaryZone -Name "realms2riches.com" -ZoneFile "realms2riches.com.dns"
Add-DnsServerPrimaryZone -Name "realms2riches.tech" -ZoneFile "realms2riches.tech.dns"
```

**Hyper-V Configuration:**
```powershell
# Enable Hyper-V
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Enable nested virtualization for WSL2
Set-VMProcessor -VMName "WSL" -ExposeVirtualizationExtensions $true
```

---

### 3. WSL2 Ubuntu Setup

**Installation:**
```powershell
# On Windows Server 2025
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

**Docker Installation (in WSL2):**
```bash
# Update and install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker
```

---

### 4. Docker Compose Stack

**File: `docker-compose.production.yml`**
```yaml
version: '3.8'

services:
  # Backend API
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://swarm:${DB_PASSWORD}@postgres:5432/swarm
      - REDIS_URL=redis://redis:6379/0
      - S3_ENDPOINT_URL=http://minio:9000
      - S3_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - S3_SECRET_KEY=${MINIO_SECRET_KEY}
      - OLLAMA_URL=http://192.168.1.X:11434  # Your laptop IP
      - JWT_SECRET_KEY=${JWT_SECRET}
    volumes:
      - ./output:/app/output
    depends_on:
      - postgres
      - redis
      - minio
    restart: always
    networks:
      - swarmnet

  # PostgreSQL Database (FREE)
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=swarm
      - POSTGRES_USER=swarm
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
    networks:
      - swarmnet

  # Redis Cache & Queue (FREE)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - swarmnet

  # MinIO S3-Compatible Storage (FREE)
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    volumes:
      - minio_data:/data
    restart: always
    networks:
      - swarmnet

  # ChromaDB Vector Store (FREE)
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
    restart: always
    networks:
      - swarmnet

  # Caddy Reverse Proxy (FREE)
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile
      - ./frontend/public:/srv/frontend
      - caddy_data:/data
      - caddy_config:/config
    restart: always
    networks:
      - swarmnet

volumes:
  postgres_data:
  redis_data:
  minio_data:
  chroma_data:
  caddy_data:
  caddy_config:

networks:
  swarmnet:
    driver: bridge
```

---

### 5. Caddyfile Configuration

**File: `deploy/Caddyfile`**
```caddyfile
# Main landing page
realms2riches.com, www.realms2riches.com {
    root * /srv/frontend
    file_server
    try_files {path} /index.html
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000;"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer-when-downgrade"
    }
}

# API backend
api.realms2riches.com {
    reverse_proxy backend:8000
    
    header {
        Strict-Transport-Security "max-age=31536000;"
        X-Content-Type-Options "nosniff"
    }
}

# Corporate info
corp.realms2riches.com {
    root * /srv/frontend
    file_server
    try_files {path} /corp.html
}

# MinIO Console (admin only)
minio.realms2riches.com {
    reverse_proxy minio:9001
}

# Tenant boxes (wildcard)
*.realms2riches.tech {
    reverse_proxy {
        to tenant-{labels.1}:8080
        health_uri /health
        health_interval 30s
    }
}
```

---

### 6. Environment Variables

**File: `.env.production`**
```bash
# Database
DB_PASSWORD=your-secure-password-here

# MinIO (S3)
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your-secure-minio-password

# JWT
JWT_SECRET=your-jwt-secret-key-here

# Ollama (your laptop)
OLLAMA_URL=http://192.168.1.X:11434

# Application
APP_ENV=production
DEBUG=false
```

---

## Deployment Steps

### Initial Setup

```bash
# 1. Clone repository in WSL2
cd /home/yourusername
git clone https://github.com/yourusername/SwarmEnterprise-v2.git
cd SwarmEnterprise-v2

# 2. Create environment file
cp .env.example .env.production
nano .env.production  # Edit with your values

# 3. Build and start services
docker-compose -f docker-compose.production.yml up -d

# 4. Check services
docker-compose ps

# 5. View logs
docker-compose logs -f backend

# 6. Initialize database
docker-compose exec backend python -m backend.db.init_db

# 7. Create admin user
docker-compose exec backend python -m backend.scripts.create_admin
```

### DNS Configuration

**On Windows Server 2025 DNS Manager:**
```
# A Records
realms2riches.com          → 192.168.1.Y (WSL2 IP)
www.realms2riches.com      → 192.168.1.Y
api.realms2riches.com      → 192.168.1.Y
corp.realms2riches.com     → 192.168.1.Y
minio.realms2riches.com    → 192.168.1.Y

# Wildcard for tenants
*.realms2riches.tech       → 192.168.1.Y
```

---

## Cost Analysis

### Hardware Requirements
- **Windows Server 2025 VM**: 16GB RAM, 8 CPU cores, 500GB SSD
- **Laptop for Ollama**: 16GB+ RAM, GPU optional but recommended
- **Network**: Local network connection

### Monthly Costs
| Item | Cost |
|------|------|
| Software licenses | $0 (all open source) |
| Cloud services | $0 (self-hosted) |
| Domain registration | ~$12/year ($1/mo) |
| SSL certificates | $0 (Let's Encrypt via Caddy) |
| Electricity | ~$20-50/mo (varies by location) |
| **TOTAL** | **~$21-51/mo** |

### Comparison to Cloud
| Cloud Setup | Self-Hosted | Savings |
|-------------|-------------|---------|
| $500-1000/mo | $21-51/mo | **95% reduction** |

---

## Advantages of This Setup

✅ **Zero Vendor Lock-in** - All open source  
✅ **Complete Control** - Full access to everything  
✅ **Privacy** - Data never leaves your infrastructure  
✅ **Cost Effective** - Only electricity costs  
✅ **Scalable** - Add more VMs as needed  
✅ **Professional** - Enterprise-grade stack  
✅ **Learning** - Full understanding of the system  
✅ **Customizable** - Modify anything you want  

---

## Monitoring & Maintenance

### Free Monitoring Tools

```yaml
# Add to docker-compose.yml
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: always

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    restart: always
```

### Backup Strategy (Free)

```bash
# Automated backup script
#!/bin/bash
# backup.sh

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U swarm swarm > backup_$(date +%Y%m%d).sql

# Backup MinIO data
docker-compose exec -T minio mc mirror /data /backup

# Backup to external drive
rsync -av backup_* /mnt/external_drive/swarm_backups/
```

---

## Security Considerations

### Firewall Rules (Windows Server)
```powershell
# Allow only necessary ports
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

### SSL Certificates
- Caddy automatically handles Let's Encrypt certificates
- Free, automatic renewal
- No manual certificate management needed

---

## Scaling Strategy

### Horizontal Scaling (Free)
1. Add more Hyper-V VMs for tenant isolation
2. Use Docker Swarm or Kubernetes (k3s) for orchestration
3. Add more worker nodes as needed
4. All still self-hosted and free

### Vertical Scaling
1. Increase VM resources (RAM, CPU)
2. Add more storage
3. Upgrade hardware as needed

---

## Conclusion

This architecture provides:
- **Enterprise-grade** infrastructure
- **Zero monthly costs** (except electricity)
- **Complete control** and privacy
- **Professional** setup
- **Scalable** design
- **100% open source**

Perfect for bootstrapping a business without burning cash on cloud services!