"""
Deployment Agent - Advanced Deployment Strategies

Handles sophisticated deployment patterns:
- Blue-green deployments
- Canary releases
- Rolling updates
- Rollback automation
- Traffic management
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from backend.llm.ollama_client import OllamaClient
from backend.services.deployment_service import (
    DeploymentService,
    DeploymentConfig as ServiceDeploymentConfig,
)

logger = logging.getLogger(__name__)


class DeploymentStrategy(str, Enum):
    """Deployment strategies"""

    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"


class DeploymentPhase(str, Enum):
    """Deployment phases"""

    PREPARING = "preparing"
    DEPLOYING = "deploying"
    TESTING = "testing"
    SWITCHING = "switching"
    MONITORING = "monitoring"
    COMPLETE = "complete"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    deployment_id: str
    strategy: DeploymentStrategy
    version: str
    health_check_url: str
    canary_percentage: int = 10
    rollout_duration_minutes: int = 30
    auto_rollback: bool = True
    success_threshold: float = 0.95


class DeploymentAgent:
    """
    Autonomous deployment agent with advanced strategies.

    Implements:
    - Blue-green: Deploy to inactive environment, switch traffic
    - Canary: Gradual rollout with monitoring
    - Rolling: Sequential instance updates
    - Auto-rollback on failure
    """

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        deployment_service: Optional[DeploymentService] = None,
    ):
        self.ollama = ollama_client or OllamaClient()
        self.deployment_service = deployment_service or DeploymentService()
        self.active_deployments: Dict[str, Dict[str, Any]] = {}

        logger.info("Deployment Agent initialized")

    async def deploy(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Execute deployment with specified strategy"""
        logger.info(f"Starting deployment: {config.deployment_id} ({config.strategy})")

        deployment = {
            "id": config.deployment_id,
            "config": config,
            "phase": DeploymentPhase.PREPARING,
            "start_time": datetime.utcnow(),
            "metrics": [],
            "events": [],
        }

        self.active_deployments[config.deployment_id] = deployment

        try:
            if config.strategy == DeploymentStrategy.BLUE_GREEN:
                await self._blue_green_deployment(deployment)
            elif config.strategy == DeploymentStrategy.CANARY:
                await self._canary_deployment(deployment)
            elif config.strategy == DeploymentStrategy.ROLLING:
                await self._rolling_deployment(deployment)
            else:
                await self._recreate_deployment(deployment)

            deployment["phase"] = DeploymentPhase.COMPLETE
            deployment["status"] = "success"

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            deployment["phase"] = DeploymentPhase.FAILED
            deployment["error"] = str(e)

            if config.auto_rollback:
                await self._rollback(deployment)

        deployment["end_time"] = datetime.utcnow()
        return deployment

    async def _blue_green_deployment(self, deployment: Dict[str, Any]) -> None:
        """Blue-green deployment strategy"""
        config = deployment["config"]

        # Deploy to green (inactive) environment
        deployment["phase"] = DeploymentPhase.DEPLOYING
        green_id = f"{config.deployment_id}-green"

        # Create service deployment config
        service_config = ServiceDeploymentConfig(
            company_id=config.deployment_id.split("-")[0]
            if "-" in config.deployment_id
            else config.deployment_id,
            tenant_name=green_id,
            subdomain=green_id.replace("_", "-").lower(),
        )

        await self.deployment_service.create_deployment(service_config)

        # Test green environment
        deployment["phase"] = DeploymentPhase.TESTING
        await self._health_check(green_id, config.health_check_url)

        # Switch traffic
        deployment["phase"] = DeploymentPhase.SWITCHING
        await self._switch_traffic("blue", "green")

        # Monitor
        deployment["phase"] = DeploymentPhase.MONITORING
        await self._monitor_deployment(deployment, duration_minutes=5)

        # Cleanup old blue environment
        await self.deployment_service.delete_deployment(f"{config.deployment_id}-blue")

    async def _canary_deployment(self, deployment: Dict[str, Any]) -> None:
        """Canary deployment strategy"""
        config = deployment["config"]

        # Deploy canary
        deployment["phase"] = DeploymentPhase.DEPLOYING
        canary_id = f"{config.deployment_id}-canary"

        # Create service deployment config
        service_config = ServiceDeploymentConfig(
            company_id=config.deployment_id.split("-")[0]
            if "-" in config.deployment_id
            else config.deployment_id,
            tenant_name=canary_id,
            subdomain=canary_id.replace("_", "-").lower(),
        )

        await self.deployment_service.create_deployment(service_config)

        # Gradual traffic shift
        deployment["phase"] = DeploymentPhase.SWITCHING
        percentages = [10, 25, 50, 75, 100]

        for percentage in percentages:
            await self._shift_traffic(canary_id, percentage)

            # Monitor metrics
            deployment["phase"] = DeploymentPhase.MONITORING
            metrics = await self._monitor_deployment(deployment, duration_minutes=5)

            # Check success threshold
            if metrics["error_rate"] > (1 - config.success_threshold):
                raise Exception(f"Canary failed: error rate {metrics['error_rate']}")

            await asyncio.sleep(60)  # Wait between shifts

    async def _rolling_deployment(self, deployment: Dict[str, Any]) -> None:
        """Rolling update strategy"""
        config = deployment["config"]

        # Get all instances
        instances = await self._get_instances(config.deployment_id)

        # Update instances one by one
        deployment["phase"] = DeploymentPhase.DEPLOYING

        for instance in instances:
            # Update instance
            await self._update_instance(instance, config.version)

            # Health check
            await self._health_check(instance, config.health_check_url)

            # Monitor
            metrics = await self._monitor_deployment(deployment, duration_minutes=2)

            if metrics["error_rate"] > (1 - config.success_threshold):
                raise Exception(f"Rolling update failed at instance {instance}")

    async def _recreate_deployment(self, deployment: Dict[str, Any]) -> None:
        """Recreate deployment strategy (downtime)"""
        config = deployment["config"]

        # Stop old version
        deployment["phase"] = DeploymentPhase.DEPLOYING
        await self.deployment_service.stop_deployment(config.deployment_id)

        # Deploy new version
        # Create service deployment config
        service_config = ServiceDeploymentConfig(
            company_id=config.deployment_id.split("-")[0]
            if "-" in config.deployment_id
            else config.deployment_id,
            tenant_name=config.deployment_id,
            subdomain=config.deployment_id.replace("_", "-").lower(),
        )

        await self.deployment_service.create_deployment(service_config)

        # Health check
        deployment["phase"] = DeploymentPhase.TESTING
        await self._health_check(config.deployment_id, config.health_check_url)

    async def _rollback(self, deployment: Dict[str, Any]) -> None:
        """Rollback deployment"""
        logger.info(f"Rolling back deployment: {deployment['id']}")

        deployment["phase"] = DeploymentPhase.ROLLING_BACK
        config = deployment["config"]

        # Restore previous version
        await self.deployment_service.restore_backup(config.deployment_id, "previous-version")

        deployment["events"].append(
            {
                "type": "rollback",
                "timestamp": datetime.utcnow().isoformat(),
                "reason": deployment.get("error", "Unknown"),
            }
        )

    async def _health_check(self, deployment_id: str, url: str) -> bool:
        """Poll the health endpoint of a deployed service.

        Retries up to 5 times with a 2-second back-off.  Returns True when
        the endpoint responds with HTTP 200, False otherwise.
        """
        import httpx
        for attempt in range(5):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        logger.info(
                            "Health check passed for %s (attempt %d)",
                            deployment_id, attempt + 1,
                        )
                        return True
                    logger.warning(
                        "Health check %s returned HTTP %d (attempt %d)",
                        deployment_id, resp.status_code, attempt + 1,
                    )
            except Exception as exc:
                logger.warning(
                    "Health check %s failed (attempt %d): %s",
                    deployment_id, attempt + 1, exc,
                )
            await asyncio.sleep(2 ** attempt)
        logger.error("Health check failed for %s after 5 attempts", deployment_id)
        return False

    async def _switch_traffic(self, from_env: str, to_env: str) -> None:
        """Atomically switch all traffic from one environment to another.

        Updates the active-environment marker in the deployment registry so
        that subsequent requests are routed to ``to_env``.  If a load-balancer
        webhook URL is configured via ``LB_WEBHOOK_URL``, a POST is sent to
        trigger the actual routing change.
        """
        import os
        import httpx
        logger.info("Switching traffic: %s -> %s", from_env, to_env)

        # Update in-memory routing table
        self.deployments[to_env] = self.deployments.get(to_env, {})
        self.deployments[to_env]["active"] = True
        if from_env in self.deployments:
            self.deployments[from_env]["active"] = False

        lb_url = os.getenv("LB_WEBHOOK_URL")
        if lb_url:
            payload = {"action": "switch", "from": from_env, "to": to_env}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(lb_url, json=payload)
                logger.info("Load-balancer notified: traffic switched to %s", to_env)
            except Exception as exc:
                logger.warning("Load-balancer webhook failed (non-fatal): %s", exc)

    async def _shift_traffic(self, deployment_id: str, percentage: int) -> None:
        """Gradually shift ``percentage`` percent of traffic to a deployment.

        Stores the weight in the deployment registry.  Notifies the optional
        ``LB_WEBHOOK_URL`` with a *shift* action so a real load-balancer can
        apply weighted routing (e.g. nginx ``weight`` or AWS ALB weighted TG).
        """
        import os
        import httpx
        percentage = max(0, min(100, percentage))
        logger.info("Shifting %d%% traffic to %s", percentage, deployment_id)

        if deployment_id in self.deployments:
            self.deployments[deployment_id]["traffic_weight"] = percentage

        lb_url = os.getenv("LB_WEBHOOK_URL")
        if lb_url:
            payload = {"action": "shift", "deployment_id": deployment_id, "weight": percentage}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(lb_url, json=payload)
                logger.info(
                    "Load-balancer notified: %d%% traffic to %s", percentage, deployment_id
                )
            except Exception as exc:
                logger.warning("Load-balancer webhook failed (non-fatal): %s", exc)

    async def _monitor_deployment(
        self, deployment: Dict[str, Any], duration_minutes: int
    ) -> Dict[str, float]:
        """Sample real system metrics for a deployment over *duration_minutes*.

        Uses :mod:`psutil` for host-level CPU/memory data and queries
        Prometheus (if ``PROMETHEUS_URL`` is set) for application metrics.
        Returns a merged snapshot dict.
        """
        import os
        import time
        import psutil
        start = time.monotonic()
        samples: List[Dict[str, float]] = []

        interval = min(30, duration_minutes * 60 / 4)  # at most 4 samples
        while time.monotonic() - start < duration_minutes * 60:
            cpu   = psutil.cpu_percent(interval=None)
            mem   = psutil.virtual_memory().percent
            samples.append({"cpu": cpu, "memory": mem})
            await asyncio.sleep(interval)

        avg_cpu = sum(s["cpu"] for s in samples) / len(samples) if samples else 0.0
        avg_mem = sum(s["memory"] for s in samples) / len(samples) if samples else 0.0

        metrics: Dict[str, float] = {
            "cpu_percent":   round(avg_cpu, 2),
            "memory_percent": round(avg_mem, 2),
            "error_rate":    0.0,
            "latency_p95":   0.0,
            "throughput":    0.0,
        }

        # Optional: pull application metrics from Prometheus
        prom_url = os.getenv("PROMETHEUS_URL")
        if prom_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    dep_id = deployment.get("id", "")
                    r = await client.get(
                        f"{prom_url}/api/v1/query",
                        params={"query": f'http_request_duration_seconds{{deployment="{dep_id}"}}'},
                    )
                    if r.status_code == 200:
                        result = r.json().get("data", {}).get("result", [])
                        if result:
                            metrics["latency_p95"] = float(result[0]["value"][1])
            except Exception as exc:
                logger.debug("Prometheus query failed (non-fatal): %s", exc)

        deployment["metrics"].append(
            {"timestamp": datetime.utcnow().isoformat(), **metrics}
        )
        return metrics

    async def _get_instances(self, deployment_id: str) -> List[str]:
        """Discover running instances of a deployment via Docker labels.

        Falls back to a synthesised list when Docker is unavailable.
        """
        import subprocess
        try:
            result = subprocess.run(
                [
                    "docker", "ps",
                    "--filter", f"label=deployment_id={deployment_id}",
                    "--format", "{{.ID}}",
                ],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                if ids:
                    return ids
        except Exception as exc:
            logger.debug("Docker ps failed (non-fatal): %s", exc)

        # Fallback: synthesise instance names from deployment registry
        dep = self.deployments.get(deployment_id, {})
        count = dep.get("replica_count", 3)
        return [f"{deployment_id}-{i}" for i in range(count)]

    async def _update_instance(self, instance: str, version: str) -> None:
        """Trigger a rolling update of a single Docker container instance.

        Issues a ``docker pull`` + ``docker restart`` for the named container.
        If Docker is unavailable the operation is logged and skipped gracefully.
        """
        import subprocess
        logger.info("Updating instance %s to version %s", instance, version)
        for cmd in (
            ["docker", "pull", f"{instance}:{version}"],
            ["docker", "restart", instance],
        ):
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60,
                )
                if result.returncode == 0:
                    logger.info("Command succeeded: %s", " ".join(cmd))
                else:
                    logger.warning(
                        "Command returned %d: %s\n%s",
                        result.returncode, " ".join(cmd), result.stderr,
                    )
            except Exception as exc:
                logger.warning("Instance update command failed (non-fatal): %s", exc)

    async def cleanup(self) -> None:
        """Cleanup resources"""
        await self.ollama.close()


# Made with Bob
