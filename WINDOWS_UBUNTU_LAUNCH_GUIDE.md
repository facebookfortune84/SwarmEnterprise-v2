# SwarmEnterprise v2 — Windows 11 + Ubuntu Hyper-V Launch Guide

**Complete deployment guide for launching from Windows 11 Pro with Ubuntu 22.04 LTS on Hyper-V**

---

## Table of Contents

1. [Windows 11 Setup](#windows-11-setup) — What to do on Windows
2. [Ubuntu Setup](#ubuntu-setup) — What to do on Ubuntu VM
3. [Verification & Access](#verification--access) — Testing the deployment
4. [Troubleshooting](#troubleshooting) — Common issues

---

## Windows 11 Setup

### Prerequisites (Do These First on Windows)

#### 1. Enable Hyper-V on Windows 11 Pro

```powershell
# Run PowerShell as Administrator
Enable-WindowsOptionalFeature -FeatureName Hyper-V -Online -All

# Restart when prompted
Restart-Computer
```

**Verify Hyper-V is enabled:**
```powershell
Get-WindowsOptionalFeature -FeatureName Hyper-V -Online | Select-Object State
# Expected output: State : Enabled
```

#### 2. Create Ubuntu 22.04 LTS Hyper-V Virtual Machine

**Using Hyper-V Manager (GUI):**
1. Open **Hyper-V Manager** (search in Start menu)
2. Click **New** → **Virtual Machine**
3. **Name:** `swarmenterprise-vm`
4. **Generation:** Generation 2
5. **Memory:** 8192 MB (8GB) — **CHECK: Use Dynamic Memory** (Min: 4096, Max: 16384)
6. **Network:** Default switch OR create new external switch
7. **Hard disk:** 80 GB
8. **Installation media:** Ubuntu 22.04 LTS ISO

**Or using PowerShell:**

```powershell
# Download Ubuntu 22.04 LTS ISO first
# https://releases.ubuntu.com/jammy/ubuntu-22.04.6-live-server-amd64.iso

$VMName = "swarmenterprise-vm"
$Memory = 8GB
$CPUs = 4
$VHDPath = "C:\Hyper-V\$VMName\disk.vhdx"
$VHDSize = 80GB
$ISOPath = "C:\ISO\ubuntu-22.04.6-live-server-amd64.iso"

# Create VM
New-VM -Name $VMName -Generation 2 -MemoryStartupBytes $Memory -NewVHDPath $VHDPath -NewVHDSizeBytes $VHDSize | Add-VMDvdDrive -Path $ISOPath

# Configure CPU and memory
Set-VMProcessor -VMName $VMName -Count $CPUs
Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $true -MinimumBytes 4GB -MaximumBytes 16GB

# Start VM
Start-VM -Name $VMName
```

#### 3. Install Ubuntu 22.04 LTS on the VM

1. Start the VM and attach the ISO
2. Boot from ISO
3. Choose **Ubuntu Server (automated install)**
4. Follow the installer:
   - **Language:** English
   - **Keyboard:** Your layout
   - **Network:** DHCP (automatic)
   - **Storage:** Accept default (use entire disk)
   - **Profile name:** `ubuntu` or your preferred username
   - **Password:** Strong password (save it!)
   - **SSH:** Enable (Yes, install OpenSSH server)
5. **Reboot** when complete

#### 4. Configure Network on Hyper-V VM

After Ubuntu boots, get the VM's IP address:

```bash
# Inside Ubuntu VM
hostname -I
# Output: 192.168.1.100 (or similar)
```

**From Windows, add to your `hosts` file** (optional but recommended):

```powershell
# Windows PowerShell (as Administrator)
$HostsPath = "C:\Windows\System32\drivers\etc\hosts"

# Add VM IP
Add-Content -Path $HostsPath -Value "`n192.168.1.100	swarmenterprise-vm.local"
```

#### 5. Set Up SSH Access from Windows to Ubuntu

**On Windows (PowerShell as Admin):**

```powershell
# Generate SSH key pair (if you don't have one)
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519"

# Copy public key to clipboard
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | Set-Clipboard

# Test connection
ssh ubuntu@192.168.1.100  # or swarmenterprise-vm.local
# Paste your public key when prompted, or use password
```

**On Ubuntu VM:**

```bash
# Inside the Ubuntu VM
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Paste your Windows public key
nano ~/.ssh/authorized_keys
# (Paste, Ctrl+O, Enter, Ctrl+X)

chmod 600 ~/.ssh/authorized_keys
```

#### 6. Transfer Launch Script to Ubuntu VM

**From Windows (PowerShell):**

```powershell
# Copy the launch script to the Ubuntu VM
scp -r "C:\SwarmEnterprise-v2\launch_ubuntu.sh" ubuntu@192.168.1.100:/home/ubuntu/

# Or use WinSCP for GUI transfer
# https://winscp.net/
```

---

## Ubuntu Setup

### On the Ubuntu 22.04 LTS Hyper-V VM

#### 1. SSH Into Ubuntu from Windows

```powershell
# From Windows PowerShell
ssh ubuntu@192.168.1.100
# or
ssh ubuntu@swarmenterprise-vm.local
```

#### 2. Run the Automated Launch Script

```bash
# Inside Ubuntu terminal
cd /home/ubuntu

# Make script executable
chmod +x launch_ubuntu.sh

# Run the script (this takes 10–15 minutes)
bash launch_ubuntu.sh
```

**What this script does (fully automated):**
- ✅ Updates system packages (`apt update && apt upgrade`)
- ✅ Installs Docker, Docker Compose, Python 3.11, Git
- ✅ Clones SwarmEnterprise repository to `/opt/swarmenterprise`
- ✅ Generates secure secrets (JWT keys, encryption keys)
- ✅ Configures .env file
- ✅ Starts PostgreSQL and Redis containers
- ✅ Runs database migrations (Alembic)
- ✅ Seeds initial data
- ✅ Starts FastAPI backend

**Expected output:**
```
========================================================================
SwarmEnterprise v2 — LAUNCH COMPLETE!
========================================================================

[OK] All services are running:
CONTAINER ID   IMAGE         STATUS           PORTS
xxx            postgres:16   Up 2 minutes     5432->5432/tcp
xxx            redis:7       Up 2 minutes     6379->6379/tcp
xxx            backend       Up 1 minute      8000->8000/tcp

========================================================================
NEXT STEPS
========================================================================

Admin Email:    admin@localhost
Admin Password: AdminPassword123!
```

#### 3. Manual Alternative (If Script Fails)

If the script encounters issues, run these commands manually:

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y curl gnupg lsb-release ca-certificates
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Install Python 3.11
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install Git
sudo apt-get install -y git

# Clone repository
sudo mkdir -p /opt/swarmenterprise
cd /opt/swarmenterprise
sudo git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git .

# Generate secrets
python3 scripts/generate_secrets.py

# Copy env and edit
cp .env.example .env
# Edit .env with your values
nano .env

# Start services
docker compose up -d postgres redis

# Wait for them to be ready
sleep 10

# Run migrations
python3 scripts/run_alembic.py upgrade head

# Seed data
python3 scripts/seed.py

# Start backend
docker compose up -d backend

# Verify
docker compose ps
curl http://localhost:8000/health
```

#### 4. Manage Services from Ubuntu

```bash
# Check status
docker compose ps

# View logs
docker compose logs -f backend

# Restart backend
docker compose restart backend

# Stop all services
docker compose down

# Start all services
docker compose up -d
```

---

## Verification & Access

### From Windows

#### 1. Access API from Windows Browser

Once the Ubuntu VM is running and backend is healthy:

```
http://192.168.1.100:8000/
http://192.168.1.100:8000/docs       (Swagger UI)
http://192.168.1.100:8000/health     (Health check)
http://192.168.1.100:8000/metrics    (Prometheus metrics)
```

Or if you added the hosts entry:

```
http://swarmenterprise-vm.local:8000/
```

#### 2. Test API from PowerShell

```powershell
# Health check
$response = Invoke-RestMethod -Uri "http://192.168.1.100:8000/health" -Method Get
$response | ConvertTo-Json

# Should return:
# {
#   "status": "ONLINE",
#   "version": "2.0.0",
#   "engine": "SwarmOS",
#   "checks": {
#     "db": "ok",
#     "redis": "ok",
#     "ollama": "unreachable"
#   }
# }
```

#### 3. Port Forward (Optional)

If you want to access from outside your local network:

**Windows PowerShell (as Admin):**

```powershell
# Forward Windows port 8000 to VM port 8000
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=192.168.1.100

# Verify
netsh interface portproxy show all

# Access from other machines
http://your-windows-ip:8000
```

### From Ubuntu VM

```bash
# Inside Ubuntu VM
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Will return HTML

# Tail logs
docker compose logs -f backend

# Check database
docker compose exec postgres psql -U postgres -d docker -c "SELECT * FROM information_schema.tables WHERE table_schema='public';"
```

---

## Troubleshooting

### Issue: Script fails with "Docker daemon not accessible"

**Solution:**

```bash
# Add ubuntu user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker ps
```

### Issue: "could not translate host name 'postgres'"

**Solution:** This is normal if running migrations before Docker containers are fully ready. The script has delays to prevent this.

```bash
# Wait for containers
docker compose ps

# Try again
python3 scripts/run_alembic.py upgrade head
```

### Issue: "Port 8000 already in use"

**Solution:**

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill it (if safe)
sudo kill -9 <PID>

# Or change BACKEND_PORT in .env and restart
nano .env  # Change BACKEND_PORT to 8001
docker compose restart backend
```

### Issue: Cannot SSH from Windows to Ubuntu VM

**Solution:**

```powershell
# Verify VM is running
Get-VM swarmenterprise-vm | Select-Object Name, State

# Check VM's IP address
Get-VMNetworkAdapter -VMName swarmenterprise-vm

# Try with password first (simpler)
ssh -o PubkeyAuthentication=no ubuntu@192.168.1.100

# Then set up SSH keys once connected
```

### Issue: Backend won't start ("Alembic migration failed")

**Solution:**

```bash
# Check database is ready
docker compose exec postgres pg_isready -U postgres

# Check migration status
docker compose exec backend alembic current

# Downgrade one step and retry
docker compose exec backend alembic downgrade -1

# Then upgrade
docker compose exec backend alembic upgrade head
```

### Issue: "Health check timeout"

**Solution:**

```bash
# Check backend logs
docker compose logs backend

# May be a config error; check .env
cat .env | grep DATABASE_URL

# Restart with more time for startup
docker compose restart backend
sleep 10

# Check health
curl http://localhost:8000/health
```

---

## Production Deployment to Cloud

Once verified on the Hyper-V VM, deploy to production:

1. **Provision cloud VM** (AWS t3.large, IONOS VPS L, DigitalOcean 8GB)
2. **SSH into cloud VM**
3. **Run the same launch script:**
   ```bash
   bash launch_ubuntu.sh
   ```
4. **Configure DNS** to point to cloud VM IP
5. **Set ENV=production** in .env
6. **Set STRIPE_TEST_MODE=FALSE** if using Stripe
7. **Restart services** and verify HTTPS is working

---

## Quick Reference

### Windows Commands

```powershell
# Connect to VM
ssh ubuntu@192.168.1.100

# Copy files to VM
scp -r "C:\path\to\file" ubuntu@192.168.1.100:/home/ubuntu/

# Manage VM
Get-VM swarmenterprise-vm
Start-VM -Name swarmenterprise-vm
Stop-VM -Name swarmenterprise-vm
```

### Ubuntu Commands

```bash
# SSH from Windows
ssh ubuntu@swarmenterprise-vm.local

# Navigate to project
cd /opt/swarmenterprise

# Check services
docker compose ps
docker compose logs -f backend

# Stop/start
docker compose down
docker compose up -d
```

### API Access

| Resource | URL (Ubuntu VM) | URL (Windows Browser) |
|----------|-----------------|----------------------|
| API | http://localhost:8000 | http://192.168.1.100:8000 |
| Swagger Docs | http://localhost:8000/docs | http://192.168.1.100:8000/docs |
| Health | http://localhost:8000/health | http://192.168.1.100:8000/health |
| Metrics | http://localhost:8000/metrics | http://192.168.1.100:8000/metrics |

---

## Summary

### On Windows 11:
1. ✅ Enable Hyper-V
2. ✅ Create Ubuntu 22.04 LTS VM (8GB RAM, 80GB disk, 4 CPUs)
3. ✅ Install Ubuntu Server
4. ✅ Configure SSH access
5. ✅ Transfer `launch_ubuntu.sh` to VM
6. ✅ Access services from browser at http://192.168.1.100:8000

### On Ubuntu VM:
1. ✅ SSH in from Windows
2. ✅ Run `bash launch_ubuntu.sh`
3. ✅ Wait 10–15 minutes
4. ✅ All services auto-start
5. ✅ Verify with `docker compose ps`

### Test from Windows:
1. ✅ Browser: http://192.168.1.100:8000/docs
2. ✅ PowerShell: `Invoke-RestMethod http://192.168.1.100:8000/health`
3. ✅ Done! 🚀

---

**SwarmEnterprise v2 is live on your Hyper-V Ubuntu VM!**
