"""
Self-healing remediation: restart services, log actions, optional scheduler hook.

Run continuously:
  python -m agents.ops.scheduler
Or on demand:
  scons heal
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agents.ops.monitor import run_all_checks

logger = logging.getLogger("ops.self_heal")
HEAL_LOG = Path(os.getenv("SWARM_OUTPUT_DIR", "output")) / "ops_heal.log"


def _append_log(entry: dict):
    HEAL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HEAL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def restart_docker_service(service: str) -> dict:
    try:
        proc = subprocess.run(
            ["docker", "restart", service],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        ok = proc.returncode == 0
        return {"action": "docker_restart", "service": service, "ok": ok}
    except Exception as exc:
        return {"action": "docker_restart", "service": service, "ok": False, "error": str(exc)}


def run_heal_cycle() -> dict:
    """Detect failures and attempt automated fixes."""
    started = datetime.now(timezone.utc).isoformat()
    checks = run_all_checks()
    actions = []

    if not checks.get("backend_container", {}).get("ok"):
        actions.append(restart_docker_service("swarmOS-backend"))

    if not checks.get("redis_container", {}).get("ok"):
        actions.append(restart_docker_service("swarmOS-redis"))

    if not checks.get("ollama", {}).get("ok"):
        actions.append(
            {
                "action": "ollama_hint",
                "ok": False,
                "message": (
                    "Ensure `ollama serve` on laptop and OLLAMA_URL points to "
                    "LAPTOP LAN IP or host.docker.internal from WSL Docker"
                ),
            }
        )

    report = {
        "started": started,
        "finished": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "actions": actions,
        "healthy": all(
            checks.get(k, {}).get("ok")
            for k in ("api", "ollama", "backend_container")
            if checks.get(k) is not None
        ),
    }
    _append_log(report)
    logger.info("Heal cycle complete: healthy=%s actions=%s", report["healthy"], len(actions))
    return report
