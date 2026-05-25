"""
Deploy per-tenant Docker boxes on realms2riches.tech.

Hyper-V VM spin-up is stubbed; Docker-per-tenant is the working minimum path.
"""

import logging
import os
import re
import subprocess
import uuid
from pathlib import Path

logger = logging.getLogger("box_deployer")

TECH_DOMAIN = os.getenv("TECH_DOMAIN", "realms2riches.tech")
BOX_IMAGE = os.getenv("TENANT_BOX_IMAGE", "redis:7-alpine")
BOX_NETWORK = os.getenv("TENANT_BOX_NETWORK", "swarmnet")
REPO_ROOT = Path(os.getenv("SWARM_REPO_ROOT", Path(__file__).resolve().parents[2]))


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", name.lower().strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:48] or f"tenant-{uuid.uuid4().hex[:6]}"


class BoxDeployer:
    """Docker-based tenant isolation (one container per company)."""

    def provision_hyperv_vm(self, tenant_id: str, vm_name: str) -> dict:
        """
        Stub for Hyper-V VM creation. See scripts/hyperv/provision_vm.ps1.
        """
        script = REPO_ROOT / "scripts" / "hyperv" / "provision_vm.ps1"
        if script.exists():
            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script),
                        "-TenantId",
                        tenant_id,
                        "-VmName",
                        vm_name,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
                if result.returncode == 0:
                    return {
                        "status": "submitted",
                        "vm_name": vm_name,
                        "stdout": result.stdout[-500:],
                    }
            except Exception as exc:
                logger.warning("Hyper-V script failed: %s", exc)
        return {
            "status": "stub",
            "message": "Hyper-V automation not run; use Docker box path",
            "vm_name": vm_name,
        }

    def deploy_docker_box(self, slug: str, tenant_id: str) -> dict:
        """Start an isolated container for the tenant on the Docker host."""
        container_name = f"r2r-box-{slug}"
        subdomain = f"{slug}.{TECH_DOMAIN}"
        box_url = f"https://{subdomain}"

        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "--label",
            f"swarm.tenant_id={tenant_id}",
            "--label",
            f"swarm.subdomain={subdomain}",
            "--network",
            BOX_NETWORK,
            "-e",
            f"TENANT_ID={tenant_id}",
            "-e",
            f"TENANT_SLUG={slug}",
            BOX_IMAGE,
        ]
        try:
            # Remove stale container if present
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=30,
                check=False,
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
            if proc.returncode != 0:
                return {
                    "status": "failed",
                    "container_id": None,
                    "box_url": box_url,
                    "error": (proc.stderr or proc.stdout or "docker run failed")[:500],
                }
            container_id = (proc.stdout or "").strip()[:64]
            return {
                "status": "running",
                "container_id": container_id,
                "container_name": container_name,
                "box_url": box_url,
                "subdomain": subdomain,
            }
        except FileNotFoundError:
            return {
                "status": "failed",
                "error": "docker CLI not found on host",
                "box_url": box_url,
            }
        except Exception as exc:
            logger.exception("Docker deploy failed")
            return {"status": "failed", "error": str(exc)[:500], "box_url": box_url}

    def box_status(self, slug: str) -> dict:
        container_name = f"r2r-box-{slug}"
        try:
            proc = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Status}}",
                    container_name,
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if proc.returncode != 0:
                return {"status": "not_found", "container_name": container_name}
            return {
                "status": proc.stdout.strip() or "unknown",
                "container_name": container_name,
            }
        except FileNotFoundError:
            return {"status": "docker_unavailable"}

    def stop_box(self, slug: str) -> dict:
        container_name = f"r2r-box-{slug}"
        try:
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                timeout=30,
                check=False,
            )
            return {"status": "stopped", "container_name": container_name}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
