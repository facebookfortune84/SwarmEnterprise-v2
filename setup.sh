#!/bin/bash

set -e

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "=========================================="
echo "SwarmOS Setup: Environment & Dependencies"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}[1/6] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[2/6] Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate venv
echo -e "${BLUE}[3/6] Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo -e "${BLUE}[4/6] Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel --quiet
echo -e "${GREEN}✓ pip upgraded${NC}"

# Install root requirements
echo -e "${BLUE}[5/6] Installing root dependencies...${NC}"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Load .env
echo -e "${BLUE}[6/6] Loading environment variables...${NC}"
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo -e "${GREEN}✓ .env loaded${NC}"
else
    echo -e "${GREEN}⚠ .env not found (using defaults)${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✓ SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Find Ollama gateway: ip route | grep default"
echo "  2. Test network bridge: python test_network_bridge.py"
echo "  3. Run backend: uvicorn backend.main:app --reload"
echo "  4. Or use Docker:     docker-compose up -d"
echo ""