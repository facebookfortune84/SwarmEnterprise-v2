import logging
import os
from pathlib import Path

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

# Enable structured JSON logging if requested (requires python-json-logger)
if os.getenv("ENABLE_JSON_LOGGING", "FALSE").lower() in ("1", "true", "yes") or os.getenv(
    "OTEL_OTLP_ENDPOINT"
):
    try:
        from pythonjsonlogger import jsonlogger

        root = logging.getLogger()
        if root.handlers:
            handler = root.handlers[0]
            fmt = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
            handler.setFormatter(fmt)
            logger.info("JSON logging enabled")
    except Exception:
        logger.warning("python-json-logger not available; falling back to text logs")

# Initialize telemetry (if available)
try:
    from backend import telemetry

    telemetry.init()
except Exception:
    logger.debug("Telemetry not initialized")

app = FastAPI(title="SwarmOS Sovereign Factory", version="2.0.0")

# Prometheus metrics endpoint
try:
    from backend.metrics import metrics_endpoint

    @app.get("/metrics")
    def metrics():
        return metrics_endpoint()

except Exception:
    logger.debug("Prometheus metrics not available")

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "https://realms2riches.com,https://www.realms2riches.com,https://corp.realms2riches.com,http://localhost:8000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()] or ["*"],
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

# Outreach API
try:
    from backend.api.outreach import router as outreach_router

    app.include_router(outreach_router)
except Exception:
    logger.debug("Outreach router not available")

try:
    from backend.api.tenants import router as tenants_router

    app.include_router(tenants_router)
except Exception:
    logger.debug("Tenants router not available")

try:
    from backend.api.ops import router as ops_router

    app.include_router(ops_router)
except Exception:
    logger.debug("Ops router not available")

# Ensure output directory exists for static files (use env override)
OUTPUT_DIR = os.getenv(
    "SWARM_OUTPUT_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "output"),
)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "src"), exist_ok=True)

# Start outreach worker
try:
    from agents.outreach.worker import start_worker

    start_worker()
except Exception:
    logger.debug("Outreach worker not started")


_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public"
if _FRONTEND_DIR.is_dir():
    app.mount("/dashboard", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="dashboard")
    app.mount("/corp", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="corp")


@app.get("/health")
def health_check():
    ollama_ok = False
    try:
        import requests

        url = os.getenv("OLLAMA_URL", "").rstrip("/")
        if url:
            r = requests.get(f"{url}/api/tags", timeout=3)
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "ONLINE",
        "version": "2.0.0",
        "engine": "SwarmOS",
        "deploy_profile": os.getenv("DEPLOY_PROFILE", "local"),
        "ollama_reachable": ollama_ok,
    }
