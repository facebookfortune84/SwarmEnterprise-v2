"""Health monitors for production self-healing."""

import logging
import os
import subprocess

import requests

logger = logging.getLogger("ops.monitor")


def check_health_endpoint(base_url: str | None = None) -> dict:
    base = (base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000")).rstrip("/")
    try:
        resp = requests.get(f"{base}/health", timeout=5)
        return {"ok": resp.status_code == 200, "status_code": resp.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def check_ollama() -> dict:
    url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        return {"ok": resp.status_code == 200, "url": url}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)[:200]}


def check_docker_service(service: str = "swarmOS-backend") -> dict:
    try:
        proc = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", service],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        status = proc.stdout.strip() if proc.returncode == 0 else "missing"
        return {"ok": status == "running", "status": status, "service": service}
    except FileNotFoundError:
        return {"ok": False, "status": "docker_unavailable"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def run_all_checks() -> dict:
    return {
        "api": check_health_endpoint(),
        "ollama": check_ollama(),
        "backend_container": check_docker_service("swarmOS-backend"),
        "redis_container": check_docker_service("swarmOS-redis"),
    }
