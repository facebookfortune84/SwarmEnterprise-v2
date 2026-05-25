"""Operations dashboard API: deployment health, Ollama, self-heal triggers."""

import logging
import os
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, BackgroundTasks

from agents.ops.self_heal import run_heal_cycle
from backend.core.tenants import tenant_service

router = APIRouter(prefix="/api/ops", tags=["Operations"])
logger = logging.getLogger("ops_api")


def _check_ollama() -> dict:
    url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    try:
        resp = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5)
        ok = resp.status_code == 200
        models = len(resp.json().get("models", [])) if ok else 0
        return {"reachable": ok, "url": url, "models": models, "status_code": resp.status_code}
    except Exception as exc:
        return {"reachable": False, "url": url, "error": str(exc)[:200]}


def _check_redis() -> dict:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=3)
        client.ping()
        return {"reachable": True, "url": redis_url.split("@")[-1]}
    except Exception as exc:
        return {"reachable": False, "url": redis_url, "error": str(exc)[:120]}


@router.get("/status")
def deployment_status():
    """Aggregate deployment topology for the dashboard."""
    ollama = _check_ollama()
    redis_status = _check_redis()
    tenants = tenant_service.list_tenants()
    running = sum(1 for t in tenants if t.get("status") == "running")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domains": {
            "primary": os.getenv("PRIMARY_DOMAIN", "realms2riches.com"),
            "corp": os.getenv("CORP_DOMAIN", "corp.realms2riches.com"),
            "api": os.getenv("API_DOMAIN", "api.realms2riches.com"),
            "tech": os.getenv("TECH_DOMAIN", "realms2riches.tech"),
        },
        "environment": os.getenv("ENV", "development"),
        "deploy_profile": os.getenv("DEPLOY_PROFILE", "local"),
        "ollama": ollama,
        "redis": redis_status,
        "tenants": {"total": len(tenants), "running": running, "items": tenants[:20]},
        "laptop_ollama_host": os.getenv("LAPTOP_OLLAMA_HOST", ""),
    }


@router.post("/heal")
def trigger_heal(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_heal_cycle)
    return {"status": "heal_started"}


@router.post("/heal-sync")
def trigger_heal_sync():
    report = run_heal_cycle()
    return report
