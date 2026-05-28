#!/bin/bash
# Sovereign Launch - Single OS, Flat Architecture
set -e

# 1. Ensure Persistence Paths
echo "📦 Preparing persistence layers..."
mkdir -p ./pg_data ./output/storage ./output/src

# 2. Check Dependencies
if [ ! -d ".venv" ]; then
    echo "⚠️ .venv not found. Running setup..."
    python3 -m venv .venv
    ./.venv/bin/pip install -r requirements.txt stripe psutil
fi

# 3. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker Desktop (Windows/WSL2)."
    exit 1
fi

# 4. Initialize Database
echo "🗄️ Initializing Database..."
export PYTHONPATH=$PYTHONPATH:.
./.venv/bin/python3.11 -c "from backend.db.session import init_db; init_db(); print('DB Ready')"

# 5. Launch Main API & Workers
echo "🚀 Launching Sovereign Factory services..."
./.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 > ./output/swarm_api.log 2>&1 &
API_PID=$!
echo "📡 Swarm API running (PID: $API_PID)"

# Start Outreach Worker (Correct path: agents/outreach/worker.py)
./.venv/bin/python3.11 agents/outreach/worker.py > ./output/outreach.log 2>&1 &
WORKER_PID=$!
echo "🤖 Outreach worker running (PID: $WORKER_PID)"

echo "✅ Sovereign Factory operational."
echo "   Monitor logs at: ./output/swarm_api.log and ./output/outreach.log"
