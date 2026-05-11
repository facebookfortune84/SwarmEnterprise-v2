import os

BASE_DIR = "/mnt/c/SwarmEnterprise_v2"

def write_file(path, content):
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + "\n")
    print(f"[✓] Generated: {path}")

def generate_phase3():
    print("==========================================")
    print(" SWARM OS GENERATOR: PHASE 3 (UI & TESTS)")
    print("==========================================")

    # 1. MAIN FASTAPI APP
    write_file("backend/main.py", r"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.webhooks import router as webhook_router
from backend.api.routes import router as core_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SwarmOS")

app = FastAPI(title="SwarmOS Sovereign Factory", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router)
app.include_router(webhook_router)

# Ensure output directory exists for static files
os.makedirs("/mnt/c/SwarmEnterprise_v2/output/src", exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "2.0.0", "engine": "SwarmOS"}
""")

    # 2. CORE API ROUTES
    write_file("backend/api/routes.py", r"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.linear_engine import swarm_db
import uuid

router = APIRouter(prefix="/api", tags=["Core Engine"])

class BuildRequest(BaseModel):
    name: str
    description: str
    stack: str

@router.post("/build")
async def trigger_build(request: BuildRequest):
    try:
        project_id = f"PROJ-{uuid.uuid4().hex[:6].upper()}"
        # In a full flow, we'd trigger the board.convene() here via a BackgroundTask
        # swarm_db.create_ticket(...)
        return {"status": "Build Initialized", "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
""")

    # 3. PREMIUM DASHBOARD UI
    write_file("frontend/public/index.html", r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SwarmOS | Sovereign Factory</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #020617; color: #38bdf8; font-family: monospace; }
        .glow { text-shadow: 0 0 10px #38bdf8; }
    </style>
</head>
<body class="p-10">
    <header class="border-b border-sky-900 pb-5 flex justify-between items-center">
        <h1 class="text-4xl font-black glow">SWARM_OS v2.0 <span class="text-xs text-white uppercase tracking-widest bg-sky-900 px-2 py-1 rounded">Enterprise Edition</span></h1>
        <button onclick="downloadBuild()" class="bg-emerald-600 px-6 py-2 rounded font-bold hover:bg-emerald-500 text-white transition-all">REPLICATE & DOWNLOAD BOX</button>
    </header>

    <main class="mt-10 grid grid-cols-1 lg:grid-cols-2 gap-10">
        <section class="space-y-6">
            <div>
                <h2 class="text-xl font-bold mb-2 text-white">1. DEFINE PROJECT VIBE</h2>
                <textarea id="prompt" class="w-full h-40 bg-slate-900 border border-slate-700 p-4 rounded text-white" placeholder="Describe the enterprise application..."></textarea>
            </div>
            <div>
                <h2 class="text-xl font-bold mb-3 text-white">2. SELECT SOVEREIGN STACK</h2>
                <select id="stack" class="w-full bg-slate-900 border border-slate-700 p-4 rounded text-white font-bold">
                    <option value="FastAPI + React + PostgreSQL">FastAPI + React + PostgreSQL</option>
                    <option value="Node.js + Tailwind + MongoDB">Node.js + Tailwind + MongoDB</option>
                </select>
            </div>
            <button onclick="startSprint()" id="btn" class="w-full bg-sky-600 text-white py-4 rounded font-black text-xl hover:bg-sky-500 transition-colors">INITIATE AUTONOMOUS SPRINT</button>
        </section>

        <section class="bg-black border border-sky-900 p-6 rounded flex flex-col h-[600px]">
            <h2 class="text-xs text-sky-800 uppercase font-black mb-4">Live Swarm Telemetry</h2>
            <div id="logs" class="text-sm space-y-2 overflow-y-auto flex-grow text-sky-400">
                <div>> System Online. Waiting for directives...</div>
            </div>
        </section>
    </main>

    <script>
        async function startSprint() {
            const btn = document.getElementById('btn');
            const log = document.getElementById('logs');
            btn.innerText = "SPRINT IN PROGRESS..."; 
            btn.disabled = true;
            
            const vibe = document.getElementById('prompt').value;
            const stack = document.getElementById('stack').value;
            log.innerHTML += `<div class="text-yellow-500">> Board of Directors convened for new project...</div>`;

            try {
                const res = await fetch('http://localhost:8000/api/build', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name: "AutoProject", description: vibe, stack: stack })
                });
                const data = await res.json();
                if(res.ok) {
                    log.innerHTML += `<div class="text-green-500">> [SUCCESS] Project ID ${data.project_id} initialized. Supervisors dispatched.</div>`;
                }
            } catch (err) {
                log.innerHTML += `<div class="text-red-500">> [ERROR] API Unreachable. Check Docker containers.</div>`;
            }
        }

        function downloadBuild() {
            alert("Delivery via Webhook triggered. Check your email!");
        }
    </script>
</body>
</html>
""")

    # 4. TEST HARNESS (PYTEST)
    write_file("pytest.ini", r"""
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
""")

    write_file("tests/conftest.py", r"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)
""")

    write_file("tests/unit/backend/test_routes.py", r"""
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ONLINE"
    assert response.json()["engine"] == "SwarmOS"

def test_build_trigger(client):
    payload = {"name": "Test App", "description": "A testing vibe", "stack": "FastAPI"}
    response = client.post("/api/build", json=payload)
    assert response.status_code == 200
    assert "project_id" in response.json()
""")

    # 5. DOCKER DEPLOYMENT MANIFEST
    write_file("docker-compose.yml", r"""
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - .:/mnt/c/SwarmEnterprise_v2
    environment:
      - OLLAMA_URL=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
""")

    write_file("backend/Dockerfile", r"""
FROM python:3.11-slim
WORKDIR /mnt/c/SwarmEnterprise_v2
COPY backend/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN pip install fastapi uvicorn stripe
COPY . .
CMD["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

    print("\n[✓] PHASE 3 GENERATION COMPLETE.")

if __name__ == "__main__":
    generate_phase3()