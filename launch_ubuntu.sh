#!/bin/bash
# SwarmEnterprise v2 — Complete Ubuntu 22.04 LTS Launch Sequence
# 
# This script performs FULL SYSTEM SETUP on a fresh Ubuntu Hyper-V VM
# Run as: bash launch_ubuntu.sh
#
# What this does:
# 1. Update system packages
# 2. Install Docker, Docker Compose, Python 3.11, Git
# 3. Clone SwarmEnterprise repository
# 4. Configure environment
# 5. Generate secrets
# 6. Launch all services
#
# Estimated time: 10–15 minutes
# ============================================================================

set -e  # Exit on error

echo "========================================================================"
echo "SwarmEnterprise v2 — Ubuntu 22.04 LTS Launch Sequence"
echo "========================================================================"
echo ""

# ============================================================================
# STEP 1: System Update
# ============================================================================
echo "[STEP 1/8] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y
echo "[OK] System packages updated."
echo ""

# ============================================================================
# STEP 2: Install Docker
# ============================================================================
echo "[STEP 2/8] Installing Docker..."
sudo apt-get install -y curl gnupg lsb-release ca-certificates

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add current user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker
docker --version
docker compose version

echo "[OK] Docker installed and configured."
echo ""

# ============================================================================
# STEP 3: Install Python 3.11 and tools
# ============================================================================
echo "[STEP 3/8] Installing Python 3.11 and development tools..."
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set Python 3.11 as default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Verify Python
python3 --version
pip3 --version

echo "[OK] Python 3.11 installed."
echo ""

# ============================================================================
# STEP 4: Install Git and other tools
# ============================================================================
echo "[STEP 4/8] Installing Git and utilities..."
sudo apt-get install -y git wget curl jq htop

# Verify Git
git --version

echo "[OK] Git and utilities installed."
echo ""

# ============================================================================
# STEP 5: Clone SwarmEnterprise repository
# ============================================================================
echo "[STEP 5/8] Cloning SwarmEnterprise v2 repository..."

# Create deployment directory
DEPLOY_DIR="/opt/swarmenterprise"
if [ -d "$DEPLOY_DIR" ]; then
    echo "[WARN] $DEPLOY_DIR already exists. Pulling latest changes..."
    cd "$DEPLOY_DIR"
    git pull origin main
else
    echo "[INFO] Cloning repository to $DEPLOY_DIR..."
    sudo mkdir -p "$DEPLOY_DIR"
    sudo git clone https://github.com/rwv-techsolutions/swarmenterprise-v2.git "$DEPLOY_DIR"
    sudo chown -R $USER:$USER "$DEPLOY_DIR"
fi

cd "$DEPLOY_DIR"
echo "[OK] Repository ready at $DEPLOY_DIR"
echo ""

# ============================================================================
# STEP 6: Generate secrets and configure environment
# ============================================================================
echo "[STEP 6/8] Generating secrets and environment..."

# Copy environment template
cp .env.example .env

# Generate secrets
python3 scripts/generate_secrets.py > /tmp/secrets.txt

# Extract generated secrets
JWT_SECRET=$(grep "^JWT_SECRET_KEY=" /tmp/secrets.txt | cut -d'=' -f2)
SECRET_KEY=$(grep "^SECRET_KEY=" /tmp/secrets.txt | cut -d'=' -f2)
POSTGRES_PASS=$(grep "^POSTGRES_PASSWORD=" /tmp/secrets.txt | cut -d'=' -f2)
ENCRYPTION_KEY=$(grep "^ENCRYPTION_KEY=" /tmp/secrets.txt | cut -d'=' -f2)

# Update .env with generated secrets
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${JWT_SECRET}/" .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${POSTGRES_PASS}/" .env
sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=${ENCRYPTION_KEY}/" .env

# Set admin password
ADMIN_PASS="AdminPassword123!"
sed -i "s/ADMIN_PASSWORD=.*/ADMIN_PASSWORD=${ADMIN_PASS}/" .env

# Set for local/development
sed -i "s/ENV=.*/ENV=development/" .env
sed -i "s/DEPLOY_PROFILE=.*/DEPLOY_PROFILE=local/" .env
sed -i "s/BACKEND_PORT=.*/BACKEND_PORT=8000/" .env
sed -i "s/PRIMARY_DOMAIN=.*/PRIMARY_DOMAIN=localhost/" .env

echo "[OK] Environment configured."
echo ""
echo "    Generated secrets stored in .env"
echo "    Admin user: admin"
echo "    Admin password: $ADMIN_PASS"
echo "    JWT_SECRET_KEY: ${JWT_SECRET:0:16}..."
echo ""

# ============================================================================
# STEP 7: Start Docker services
# ============================================================================
echo "[STEP 7/8] Starting Docker services (PostgreSQL, Redis, Backend)..."

# Start PostgreSQL and Redis
docker compose -f docker-compose.yml up -d postgres redis

# Wait for services to be ready
echo "[INFO] Waiting for PostgreSQL and Redis to be healthy..."
for i in {1..30}; do
    if docker compose exec postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "[OK] PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[ERROR] PostgreSQL did not become ready in time"
        exit 1
    fi
    sleep 2
done

for i in {1..10}; do
    if docker compose exec redis redis-cli ping > /dev/null 2>&1; then
        echo "[OK] Redis is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "[ERROR] Redis did not become ready in time"
        exit 1
    fi
    sleep 1
done

echo ""

# ============================================================================
# STEP 8: Run database migrations and start backend
# ============================================================================
echo "[STEP 8/8] Running database migrations and starting backend..."

# Run migrations
echo "[INFO] Running Alembic migrations..."
python3 scripts/run_alembic.py upgrade head

# Seed initial data
echo "[INFO] Seeding initial data..."
python3 scripts/seed.py

# Start backend service
echo "[INFO] Starting FastAPI backend..."
docker compose -f docker-compose.yml up -d backend

# Wait for backend to be healthy
echo "[INFO] Waiting for backend to be healthy..."
for i in {1..60}; do
    if docker compose exec backend curl -s http://localhost:8000/health > /dev/null 2>&1; then
        HEALTH=$(docker compose exec backend curl -s http://localhost:8000/health | jq '.status' 2>/dev/null || echo '"OFFLINE"')
        if [ "$HEALTH" = '"ONLINE"' ]; then
            echo "[OK] Backend is online and healthy"
            break
        fi
    fi
    if [ $i -eq 60 ]; then
        echo "[WARN] Backend health check timed out; may still be starting"
        break
    fi
    sleep 1
done

echo ""

# ============================================================================
# FINAL STATUS
# ============================================================================
echo "========================================================================"
echo "SwarmEnterprise v2 — LAUNCH COMPLETE!"
echo "========================================================================"
echo ""
echo "[OK] All services are running:"
echo ""

docker compose ps

echo ""
echo "========================================================================"
echo "NEXT STEPS"
echo "========================================================================"
echo ""
echo "1. Verify API is responding:"
echo "   curl http://localhost:8000/health"
echo ""
echo "2. Access Swagger API Docs:"
echo "   http://localhost:8000/docs"
echo ""
echo "3. Check logs:"
echo "   docker compose logs -f backend"
echo ""
echo "4. Create additional workers (optional):"
echo "   docker compose -f docker-compose.yml --profile workers up -d worker beat"
echo ""
echo "5. View Flower task monitor (if workers running):"
echo "   http://localhost:5555"
echo ""
echo "6. Stop all services:"
echo "   docker compose down"
echo ""
echo "========================================================================"
echo "ADMIN CREDENTIALS"
echo "========================================================================"
echo "Email:    admin@localhost"
echo "Password: $ADMIN_PASS"
echo ""
echo "Store these securely. Save the secrets from .env in your secrets manager."
echo "========================================================================"
echo ""
echo "[SUCCESS] SwarmEnterprise v2 is live at http://localhost:8000"
echo ""
