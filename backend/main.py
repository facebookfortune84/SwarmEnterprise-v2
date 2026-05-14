import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.webhooks import router as webhook_router
from backend.api.routes import router as core_router
from backend.api.payments import router as payments_router
from backend.api.admin import router as admin_router
from backend.api.voice import router as voice_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SwarmOS")

# Initialize telemetry (if available)
try:
    from backend import telemetry
    telemetry.init()
except Exception:
    logger.debug("Telemetry not initialized")

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
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(voice_router)

# Leads API
try:
    from backend.api.leads import router as leads_router
    app.include_router(leads_router)
except Exception:
    logger.debug("Leads router not available")

# Usage API
try:
    from backend.api.usage import router as usage_router
    app.include_router(usage_router)
except Exception:
    logger.debug("Usage router not available")

# Ensure output directory exists for static files (use env override)
OUTPUT_DIR = os.getenv('SWARM_OUTPUT_DIR', '/mnt/c/SwarmEnterprise_v2/output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, 'src'), exist_ok=True)

# Start outreach worker
try:
    from agents.outreach.worker import start_worker
    start_worker()
except Exception:
    logger.debug("Outreach worker not started")

@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "2.0.0", "engine": "SwarmOS"}
