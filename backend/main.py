import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from backend.api.webhooks import router as webhook_router
from backend.api.routes import router as core_router
from backend.api.payments import router as payments_router
from backend.api.admin import router as admin_router
from backend.api.voice import router as voice_router
from backend.api.gdpr import router as gdpr_router
from backend.api.notifications import router as notifications_router
from backend.api.tickets import router as tickets_router
from backend.api.workflows import router as workflows_router
from backend.api.ws import router as ws_router
from backend.metrics import get_metrics_response, track_request

# ── Config validation (fail-fast on startup if required vars are missing) ──────
try:
    from backend.config import settings as _settings  # noqa: F401

    _cfg_ok_msg = (
        f"Config loaded | DB={_settings.database.url.split('///')[-1]} "
        f"| Redis={_settings.redis.host}:{_settings.redis.port} "
        f"| JWT_EXPIRE={_settings.jwt.access_token_expire_minutes}m"
    )
    # Logger not yet configured here; print so it appears before logging init
    print("[SwarmConfig] " + _cfg_ok_msg)
except Exception as _cfg_exc:
    import sys

    print(f"[SwarmConfig] STARTUP ABORTED — configuration error: {_cfg_exc}", flush=True)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
_ENV = os.getenv("ENV", "development").lower()
_LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)

if _ENV == "production" or os.getenv("ENABLE_JSON_LOGGING", "").lower() in ("1", "true", "yes"):
    try:
        from pythonjsonlogger import jsonlogger

        _handler = logging.StreamHandler()
        _handler.setFormatter(
            jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
                rename_fields={"asctime": "ts", "levelname": "level"},
            )
        )
        logging.basicConfig(level=_LOG_LEVEL, handlers=[_handler])
    except ImportError:
        # python-json-logger not installed — fall back to plain text
        logging.basicConfig(
            level=_LOG_LEVEL,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
else:
    # Human-readable for local dev
    logging.basicConfig(
        level=_LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

logger = logging.getLogger("SwarmOS")

# Enable structured JSON logging if OTEL endpoint present (legacy guard)
if os.getenv("OTEL_OTLP_ENDPOINT"):
    try:
        from pythonjsonlogger import jsonlogger

        root = logging.getLogger()
        if root.handlers:
            handler = root.handlers[0]
            fmt = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
            handler.setFormatter(fmt)
            logger.info("JSON logging enabled (OTEL endpoint detected)")
    except Exception:
        logger.warning("python-json-logger not available; falling back to text logs")

# Initialize telemetry (if available)
try:
    from backend import telemetry

    telemetry.init()
except Exception:
    logger.debug("Telemetry not initialized")

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title="SwarmOS Sovereign Factory", version="2.0.0")


# ---------------------------------------------------------------------------
# Middleware 1 — Request correlation ID (X-Request-ID on every response)
# ---------------------------------------------------------------------------
class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique X-Request-ID to every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Make it available to downstream handlers via request.state
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(CorrelationIDMiddleware)


# ---------------------------------------------------------------------------
# Middleware 2 — Prometheus metrics
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    track_request(
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response


# ---------------------------------------------------------------------------
# Prometheus endpoint
# ---------------------------------------------------------------------------
@app.get("/metrics")
def metrics():
    return get_metrics_response()


# ---------------------------------------------------------------------------
# CORS — wildcard only in non-production environments
# ---------------------------------------------------------------------------
_cors_raw = os.getenv(
    "CORS_ORIGINS",
    "https://realms2riches.com,https://www.realms2riches.com,https://corp.realms2riches.com,http://localhost:8000",
)
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

if _ENV == "production" and (not _cors_origins or _cors_origins == ["*"]):
    logger.warning(
        "CORS_ORIGINS is wildcard ('*') in production — "
        "set CORS_ORIGINS to your domain(s) in .env"
    )
    _cors_origins = []  # deny all cross-origin in production if not configured

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or (["*"] if _ENV != "production" else []),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(core_router)
app.include_router(webhook_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(voice_router)
app.include_router(gdpr_router)

# Phase 2 — Communication, Ticketing, Task Queue, Workflow, WebSocket
app.include_router(notifications_router)
app.include_router(tickets_router)
app.include_router(workflows_router)
app.include_router(ws_router)

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

# ---------------------------------------------------------------------------
# Static files / frontend
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.getenv(
    "SWARM_OUTPUT_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "output"),
)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "src"), exist_ok=True)

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public"
if _FRONTEND_DIR.is_dir():
    app.mount("/dashboard", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="dashboard")
    app.mount("/corp", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="corp")


# ---------------------------------------------------------------------------
# Startup event — config validation + DB connectivity check
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    # 1. Validate critical config
    _missing = []
    for var in ("JWT_SECRET_KEY", "SECRET_KEY"):
        if not os.getenv(var):
            _missing.append(var)
    if _missing:
        logger.warning(
            "Startup: missing environment variable(s): %s — "
            "some auth features will not work correctly.",
            ", ".join(_missing),
        )

    # 2. Quick DB connectivity check (non-fatal: app still starts)
    try:
        db_url = os.getenv("DATABASE_URL", "")
        if db_url:
            import asyncio
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text

            _engine = create_async_engine(db_url, pool_pre_ping=True, pool_size=1)
            async with _engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await _engine.dispose()
            logger.info("Startup: database connectivity OK")
        else:
            logger.debug("Startup: DATABASE_URL not set — skipping DB connectivity check")
    except Exception as exc:
        logger.warning("Startup: database connectivity check failed: %s", exc)

    # 3. Outreach worker + lead discovery (existing behaviour, kept intact)
    try:
        from agents.outreach.worker import start_worker

        start_worker()

        import asyncio
        from agents.marketing.lead_discovery import lead_discovery_agent

        asyncio.create_task(lead_discovery_agent.run_discovery_cycle())
        logger.info("Autonomous lead discovery cycle initiated at startup.")
    except Exception:
        logger.debug("Outreach worker or discovery not started")

    # 4. Phase 2 — initialise new DB tables and event bus subscriptions
    try:
        from backend.db.session import init_db

        init_db()
        logger.info("Phase 2 DB tables initialised.")
    except Exception:
        logger.warning("Phase 2 DB init skipped — tables may already exist.")

    try:
        from backend.services.event_bus import event_bus  # noqa: F401

        logger.info("Phase 2 event bus subscriptions registered.")
    except Exception:
        logger.warning("Phase 2 event bus could not be initialised.")

    logger.info(
        "SwarmOS v2.0.0 started | env=%s | log_level=%s | cors_origins=%s",
        _ENV,
        _LOG_LEVEL_NAME,
        _cors_origins,
    )


# ---------------------------------------------------------------------------
# Shutdown event — drain connections
# ---------------------------------------------------------------------------
@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutdown signal received — draining connections …")
    try:
        # Give in-flight requests a moment to complete
        import asyncio

        await asyncio.sleep(0.5)
    except Exception:
        pass
    logger.info("SwarmOS shutdown complete.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
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
