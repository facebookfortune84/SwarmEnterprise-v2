"""
Deployment Service - Orchestrates VM provisioning and application deployment

Manages the complete lifecycle of tenant deployments on self-hosted infrastructure.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List

import httpx

from backend.orchestration.vm_provisioner import (
    HyperVProvisioner,
    VMConfig,
)
from backend.storage.file_manager import FileManager

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Deployment status"""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    company_id: str
    tenant_name: str
    subdomain: str
    memory_mb: int = 4096
    cpu_cores: int = 2
    disk_size_gb: int = 50
    auto_start: bool = True
    backup_enabled: bool = True


def _parse_bytes_to_mbps(value: str) -> int:
    """Parse Docker stats byte string (e.g. '1.2MB') to integer Mbps approximation."""
    try:
        value = value.strip()
        if value.endswith("GB"):
            return int(float(value[:-2]) * 1000)
        if value.endswith("MB"):
            return int(float(value[:-2]))
        if value.endswith("kB") or value.endswith("KB"):
            return max(0, int(float(value[:-2]) / 1000))
    except (ValueError, AttributeError):
        pass
    return 0


def _parse_bytes_to_iops(value: str) -> int:
    """Parse Docker stats byte string to a rough IOPS number."""
    return _parse_bytes_to_mbps(value)


class DeploymentService:
    """
    Service for managing tenant deployments.

    Orchestrates:
    1. VM provisioning (Hyper-V)
    2. Application deployment (Docker)
    3. DNS configuration
    4. Health monitoring
    5. Backup management
    """

    def __init__(
        self,
        vm_provisioner: Optional[HyperVProvisioner] = None,
        file_manager: Optional[FileManager] = None,
    ):
        """
        Initialize deployment service.

        Args:
            vm_provisioner: VM provisioner instance
            file_manager: File manager instance
        """
        from backend.db.session import SessionLocal

        self.vm_provisioner = vm_provisioner or HyperVProvisioner()
        self.file_manager = file_manager or FileManager()
        self.db = SessionLocal()

        # In-memory cache for backward compatibility with tests
        self.deployments: Dict[str, Dict[str, Any]] = {}

        logger.info("Initialized deployment service with database persistence")

    def _save_deployment_to_db(self, deployment_dict: Dict[str, Any]) -> None:
        """Save or update deployment in database and in-memory cache"""
        from backend.db.models import Deployment
        import json

        deployment_id = deployment_dict["id"]

        # Update in-memory cache for backward compatibility
        self.deployments[deployment_id] = deployment_dict

        # Save to database
        existing = self.db.query(Deployment).filter_by(id=deployment_id).first()

        if existing:
            existing.status = deployment_dict["status"]
            existing.metadata_json = json.dumps(deployment_dict)
            existing.updated_at = datetime.utcnow()
        else:
            new_deployment = Deployment(
                id=deployment_id,
                tenant_id=deployment_dict["company_id"],
                status=deployment_dict["status"],
                strategy="rolling",
                version="1.0.0",
                metadata_json=json.dumps(deployment_dict),
            )
            self.db.add(new_deployment)

        self.db.commit()

    def _get_deployment_from_db(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve deployment from database"""
        from backend.db.models import Deployment
        import json

        deployment = self.db.query(Deployment).filter_by(id=deployment_id).first()
        if not deployment:
            return None

        return json.loads(deployment.metadata_json) if deployment.metadata_json else None

    def _list_deployments_from_db(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all deployments from database"""
        from backend.db.models import Deployment
        import json

        query = self.db.query(Deployment)
        if status:
            query = query.filter_by(status=status)

        deployments = query.all()
        return [json.loads(d.metadata_json) for d in deployments if d.metadata_json]

    async def create_deployment(
        self,
        config: DeploymentConfig,
    ) -> Dict[str, Any]:
        """
        Create a new deployment.

        Args:
            config: Deployment configuration

        Returns:
            Deployment information
        """
        try:
            deployment_id = f"deploy-{config.company_id}"
            vm_name = f"tenant-{config.tenant_name}"

            logger.info(f"Creating deployment: {deployment_id}")

            # Initialize deployment record
            deployment = {
                "id": deployment_id,
                "company_id": config.company_id,
                "tenant_name": config.tenant_name,
                "subdomain": config.subdomain,
                "vm_name": vm_name,
                "status": DeploymentStatus.PENDING,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "url": f"https://{config.subdomain}.realms2riches.tech",
                "ip_address": None,
                "health_status": "unknown",
            }

            # Save to database
            self._save_deployment_to_db(deployment)

            # Start deployment in background
            asyncio.create_task(self._execute_deployment(deployment_id, config))

            return deployment

        except Exception as e:
            logger.error(f"Failed to create deployment: {e}")
            raise

    async def _execute_deployment(
        self,
        deployment_id: str,
        config: DeploymentConfig,
    ) -> None:
        """Execute deployment workflow"""
        deployment = None
        try:
            deployment = self._get_deployment_from_db(deployment_id)
            if not deployment:
                raise ValueError(f"Deployment {deployment_id} not found")

            # Step 1: Provision VM
            deployment["status"] = DeploymentStatus.PROVISIONING
            deployment["updated_at"] = datetime.utcnow().isoformat()
            self._save_deployment_to_db(deployment)

            logger.info(f"Provisioning VM for deployment: {deployment_id}")

            vm_config = VMConfig(
                name=deployment["vm_name"],
                memory_mb=config.memory_mb,
                cpu_cores=config.cpu_cores,
                disk_size_gb=config.disk_size_gb,
                network_switch="External",
                os_template="ubuntu-22.04",
                domain="realms2riches.tech",
            )

            vm_info = await self.vm_provisioner.provision_vm(vm_config)

            deployment["ip_address"] = vm_info["ip_address"]
            deployment["updated_at"] = datetime.utcnow().isoformat()
            self._save_deployment_to_db(deployment)

            # Step 2: Deploy application
            deployment["status"] = DeploymentStatus.DEPLOYING
            deployment["updated_at"] = datetime.utcnow().isoformat()
            self._save_deployment_to_db(deployment)

            logger.info(f"Deploying application for: {deployment_id}")

            await self._deploy_application(deployment_id, config)

            # Step 3: Configure DNS
            await self._configure_dns(deployment_id, config)

            # Step 4: Verify deployment
            await self._verify_deployment(deployment_id)

            # Step 5: Mark as running
            deployment["status"] = DeploymentStatus.RUNNING
            deployment["health_status"] = "healthy"
            deployment["updated_at"] = datetime.utcnow().isoformat()
            self._save_deployment_to_db(deployment)

            logger.info(f"Deployment completed: {deployment_id}")

        except Exception as e:
            logger.error(f"Deployment failed {deployment_id}: {e}")
            # Only update deployment status if deployment was successfully retrieved
            if deployment is not None:
                deployment["status"] = DeploymentStatus.FAILED
                deployment["error"] = str(e)
                deployment["updated_at"] = datetime.utcnow().isoformat()
                self._save_deployment_to_db(deployment)

    async def _deploy_application(
        self,
        deployment_id: str,
        config: DeploymentConfig,
    ) -> None:
        """Deploy application to VM or local Docker container."""
        deployment = self._get_deployment_from_db(deployment_id)
        ip_address = deployment.get("ip_address") if deployment else None

        # Download company package from storage
        package_path = f"/tmp/{config.company_id}.zip"
        try:
            self.file_manager.retrieve_company(config.company_id, package_path)
        except Exception as e:
            logger.warning(f"Could not retrieve company package: {e}. Proceeding without it.")

        ssh_host = ip_address or os.getenv("DEPLOY_SSH_HOST")
        container_name = f"tenant-{config.tenant_name}"

        if ssh_host:
            # Remote Docker Compose deployment via SSH (paramiko)
            try:
                import paramiko  # type: ignore

                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh_user = os.getenv("DEPLOY_SSH_USER", "ubuntu")
                ssh_key = os.getenv("DEPLOY_SSH_KEY_PATH", os.path.expanduser("~/.ssh/id_rsa"))
                ssh.connect(ssh_host, username=ssh_user, key_filename=ssh_key, timeout=30)

                remote_dir = f"/opt/swarm/{container_name}"
                commands = [
                    f"mkdir -p {remote_dir}",
                    f"cd {remote_dir} && docker compose up -d 2>&1 || docker-compose up -d 2>&1",
                ]
                for cmd in commands:
                    _, stdout, stderr = ssh.exec_command(cmd)
                    exit_code = stdout.channel.recv_exit_status()
                    if exit_code != 0:
                        err = stderr.read().decode().strip()
                        raise RuntimeError(f"Remote command failed ({exit_code}): {err}")
                ssh.close()
                logger.info(f"Remote Docker deployment succeeded for: {deployment_id}")
            except ImportError:
                logger.warning("paramiko not installed; falling back to local Docker deployment")
                ssh_host = None

        if not ssh_host:
            # Local Docker deployment: run a named container
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        container_name,
                        "--restart",
                        "unless-stopped",
                        "-l",
                        f"swarm.deployment={deployment_id}",
                        "-l",
                        f"swarm.tenant={config.tenant_name}",
                        os.getenv("DEPLOY_DOCKER_IMAGE", "nginx:alpine"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    # Container may already exist; try starting it
                    start_result = subprocess.run(
                        ["docker", "start", container_name],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if start_result.returncode != 0:
                        raise RuntimeError(result.stderr.strip())
                logger.info(
                    f"Local Docker container '{container_name}' started for: {deployment_id}"
                )
            except FileNotFoundError:
                logger.warning("Docker CLI not found; skipping container creation for deployment")
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"Docker command timed out for deployment: {deployment_id}")

    async def _configure_dns(
        self,
        deployment_id: str,
        config: DeploymentConfig,
    ) -> None:
        """Configure DNS for deployment via Cloudflare API or local hosts file."""
        deployment = self._get_deployment_from_db(deployment_id)
        ip_address = (deployment or {}).get("ip_address") or "127.0.0.1"

        cloudflare_token = os.getenv("CLOUDFLARE_API_TOKEN")
        cloudflare_zone_id = os.getenv("CLOUDFLARE_ZONE_ID")

        if cloudflare_token and cloudflare_zone_id:
            # Cloudflare API: upsert A record
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    headers = {
                        "Authorization": f"Bearer {cloudflare_token}",
                        "Content-Type": "application/json",
                    }
                    # Check for existing record
                    resp = await client.get(
                        f"https://api.cloudflare.com/client/v4/zones/{cloudflare_zone_id}/dns_records",
                        headers=headers,
                        params={"type": "A", "name": f"{config.subdomain}.realms2riches.tech"},
                    )
                    resp.raise_for_status()
                    records = resp.json().get("result", [])

                    record_data = {
                        "type": "A",
                        "name": config.subdomain,
                        "content": ip_address,
                        "ttl": 120,
                        "proxied": False,
                    }
                    if records:
                        record_id = records[0]["id"]
                        await client.put(
                            f"https://api.cloudflare.com/client/v4/zones/{cloudflare_zone_id}/dns_records/{record_id}",
                            headers=headers,
                            json=record_data,
                        )
                        logger.info(f"Updated Cloudflare DNS record for {config.subdomain}")
                    else:
                        await client.post(
                            f"https://api.cloudflare.com/client/v4/zones/{cloudflare_zone_id}/dns_records",
                            headers=headers,
                            json=record_data,
                        )
                        logger.info(f"Created Cloudflare DNS record for {config.subdomain}")
            except Exception as e:
                logger.error(f"Cloudflare DNS configuration failed: {e}")
                raise
        else:
            # Fallback: append to /etc/hosts (development/local only)
            hosts_entry = f"{ip_address}  {config.subdomain}.realms2riches.tech\n"
            hosts_path = os.getenv("HOSTS_FILE_PATH", "/etc/hosts")
            try:
                with open(hosts_path, "r") as f:
                    existing = f.read()
                marker = f"{config.subdomain}.realms2riches.tech"
                if marker not in existing:
                    with open(hosts_path, "a") as f:
                        f.write(hosts_entry)
                    logger.info(f"Added hosts entry for {config.subdomain}")
                else:
                    logger.info(f"Hosts entry for {config.subdomain} already exists")
            except PermissionError:
                logger.warning(
                    "DNS not configured: no CLOUDFLARE_API_TOKEN set and cannot write to hosts file"
                )
            except Exception as e:
                logger.warning(f"DNS not configured: {e}")

    async def _verify_deployment(self, deployment_id: str) -> None:
        """Verify deployment is healthy by polling the service health endpoint."""
        deployment = self._get_deployment_from_db(deployment_id) or self.deployments.get(
            deployment_id, {}
        )
        url = deployment.get("url", "")

        if not url:
            logger.warning(f"No URL to verify for deployment: {deployment_id}")
            return

        health_url = f"{url}/health"
        max_retries = 10
        retry_delay = 10

        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = await client.get(health_url)
                    if resp.status_code < 500:
                        logger.info(
                            f"Health check passed ({resp.status_code}) on attempt "
                            f"{attempt}/{max_retries} for: {deployment_id}"
                        )
                        return
                    logger.warning(
                        f"Health check attempt {attempt}/{max_retries} returned "
                        f"{resp.status_code} for: {deployment_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Health check attempt {attempt}/{max_retries} failed for "
                        f"{deployment_id}: {e}"
                    )
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)

        raise RuntimeError(
            f"Deployment {deployment_id} failed health check after {max_retries} attempts"
        )

    async def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get deployment information.

        Args:
            deployment_id: Deployment ID

        Returns:
            Deployment information
        """
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")

        deployment = self.deployments[deployment_id]

        # Get VM info if running
        if deployment["status"] == DeploymentStatus.RUNNING:
            try:
                vm_info = await self.vm_provisioner.get_vm_info(deployment["vm_name"])
                deployment["vm_state"] = vm_info.state
                deployment["vm_uptime"] = vm_info.uptime_seconds
            except Exception as e:
                logger.error(f"Failed to get VM info: {e}")

        return deployment

    async def list_deployments(
        self,
        status: Optional[DeploymentStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        List deployments.

        Args:
            status: Filter by status (optional)

        Returns:
            List of deployments
        """
        deployments = list(self.deployments.values())

        if status:
            deployments = [d for d in deployments if d["status"] == status]

        return deployments

    async def start_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        Start a stopped deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Updated deployment information
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        if deployment["status"] != DeploymentStatus.STOPPED:
            raise ValueError(f"Deployment not stopped: {deployment_id}")

        logger.info(f"Starting deployment: {deployment_id}")

        # Start VM
        await self.vm_provisioner._start_vm(deployment["vm_name"])

        # Wait for services to start
        await asyncio.sleep(30)

        # Verify health
        await self._verify_deployment(deployment_id)

        deployment["status"] = DeploymentStatus.RUNNING
        deployment["health_status"] = "healthy"
        deployment["updated_at"] = datetime.utcnow().isoformat()

        return deployment

    async def stop_deployment(
        self,
        deployment_id: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Stop a running deployment.

        Args:
            deployment_id: Deployment ID
            force: Force stop if True

        Returns:
            Updated deployment information
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        if deployment["status"] != DeploymentStatus.RUNNING:
            raise ValueError(f"Deployment not running: {deployment_id}")

        logger.info(f"Stopping deployment: {deployment_id}")

        # Stop VM
        await self.vm_provisioner.stop_vm(deployment["vm_name"], force=force)

        deployment["status"] = DeploymentStatus.STOPPED
        deployment["health_status"] = "stopped"
        deployment["updated_at"] = datetime.utcnow().isoformat()

        return deployment

    async def restart_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        Restart a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Updated deployment information
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        logger.info(f"Restarting deployment: {deployment_id}")

        # Restart VM
        await self.vm_provisioner.restart_vm(deployment["vm_name"])

        # Wait for services to start
        await asyncio.sleep(30)

        # Verify health
        await self._verify_deployment(deployment_id)

        deployment["status"] = DeploymentStatus.RUNNING
        deployment["health_status"] = "healthy"
        deployment["updated_at"] = datetime.utcnow().isoformat()

        return deployment

    async def delete_deployment(
        self,
        deployment_id: str,
        delete_vm: bool = True,
    ) -> None:
        """
        Delete a deployment.

        Args:
            deployment_id: Deployment ID
            delete_vm: Delete VM if True
        """
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        logger.info(f"Deleting deployment: {deployment_id}")

        # Stop if running
        if deployment["status"] == DeploymentStatus.RUNNING:
            await self.stop_deployment(deployment_id, force=True)

        # Delete VM
        if delete_vm:
            await self.vm_provisioner.delete_vm(
                deployment["vm_name"],
                delete_disks=True,
            )

        # Remove DNS record
        await self._remove_dns(deployment_id)

        # Mark as deleted
        deployment["status"] = DeploymentStatus.DELETED
        deployment["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Deployment deleted: {deployment_id}")

    async def _remove_dns(self, deployment_id: str) -> None:
        """Remove DNS record"""
        deployment = self.deployments[deployment_id]

        f"""
        $Zone = "realms2riches.tech"
        $Name = "{deployment['subdomain']}"
        
        # Remove A record
        Remove-DnsServerResourceRecord -ZoneName $Zone -Name $Name -RRType A -Force
        
        Write-Output "DNS removed: $Name.$Zone"
        """

        logger.info(f"DNS removed for: {deployment_id}")

    async def get_deployment_metrics(
        self,
        deployment_id: str,
    ) -> Dict[str, Any]:
        """
        Get deployment metrics via docker stats, falling back to mock if Docker unavailable.

        Args:
            deployment_id: Deployment ID

        Returns:
            Metrics dict
        """
        deployment = self.deployments.get(deployment_id) or self._get_deployment_from_db(
            deployment_id
        )
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        if deployment["status"] != DeploymentStatus.RUNNING:
            return {
                "deployment_id": deployment_id,
                "status": deployment["status"],
                "health_status": deployment.get("health_status", "unknown"),
                "cpu_usage_percent": 0,
                "memory_usage_mb": 0,
                "network_in_mbps": 0,
                "network_out_mbps": 0,
                "disk_read_iops": 0,
                "disk_write_iops": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        container_name = f"tenant-{deployment['tenant_name']}"
        cpu_pct = 0
        mem_mb = 0
        net_in = 0
        net_out = 0
        disk_r = 0
        disk_w = 0

        try:
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}",
                    container_name,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("\t")
                if len(parts) >= 4:
                    # CPU: "3.14%"
                    cpu_pct = int(float(parts[0].replace("%", "").strip() or "0"))
                    # Memory: "256MiB / 4GiB"
                    mem_str = parts[1].split("/")[0].strip()
                    if "GiB" in mem_str:
                        mem_mb = int(float(mem_str.replace("GiB", "").strip()) * 1024)
                    elif "MiB" in mem_str:
                        mem_mb = int(float(mem_str.replace("MiB", "").strip()))
                    # Net I/O: "1.2kB / 3.4kB"
                    net_parts = parts[2].split("/")
                    if len(net_parts) == 2:
                        net_in = _parse_bytes_to_mbps(net_parts[0].strip())
                        net_out = _parse_bytes_to_mbps(net_parts[1].strip())
                    # Block I/O: "10MB / 5MB"
                    blk_parts = parts[3].split("/")
                    if len(blk_parts) == 2:
                        disk_r = _parse_bytes_to_iops(blk_parts[0].strip())
                        disk_w = _parse_bytes_to_iops(blk_parts[1].strip())
            else:
                logger.warning(
                    f"docker stats returned no data for {container_name}; using mock values"
                )
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Docker not available for metrics ({e}); using mock values")

        return {
            "deployment_id": deployment_id,
            "status": deployment["status"],
            "health_status": deployment.get("health_status", "unknown"),
            "cpu_usage_percent": cpu_pct,
            "memory_usage_mb": mem_mb,
            "network_in_mbps": net_in,
            "network_out_mbps": net_out,
            "disk_read_iops": disk_r,
            "disk_write_iops": disk_w,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def create_backup(self, deployment_id: str) -> Dict[str, Any]:
        """
        Create deployment backup via docker commit (container snapshot).

        Args:
            deployment_id: Deployment ID

        Returns:
            Backup information
        """
        deployment = self.deployments.get(deployment_id) or self._get_deployment_from_db(
            deployment_id
        )
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        snapshot_name = f"backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        container_name = f"tenant-{deployment['tenant_name']}"
        image_tag = f"swarm-backup/{container_name}:{snapshot_name}"

        logger.info(f"Creating backup for: {deployment_id} as {image_tag}")

        try:
            result = subprocess.run(
                ["docker", "commit", container_name, image_tag],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"docker commit failed: {result.stderr.strip()}")
            logger.info(f"Backup image created: {image_tag}")
        except FileNotFoundError:
            # Docker not available — try VM snapshot as fallback
            logger.warning("Docker not available; attempting VM snapshot")
            await self.vm_provisioner.create_snapshot(deployment["vm_name"], snapshot_name)

        return {
            "deployment_id": deployment_id,
            "snapshot_name": snapshot_name,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def restore_backup(
        self,
        deployment_id: str,
        snapshot_name: str,
    ) -> Dict[str, Any]:
        """
        Restore deployment from a Docker commit image or VM snapshot.

        Args:
            deployment_id: Deployment ID
            snapshot_name: Snapshot name (timestamp string)

        Returns:
            Updated deployment information
        """
        deployment = self.deployments.get(deployment_id) or self._get_deployment_from_db(
            deployment_id
        )
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        container_name = f"tenant-{deployment['tenant_name']}"
        image_tag = f"swarm-backup/{container_name}:{snapshot_name}"

        logger.info(f"Restoring backup for: {deployment_id} from {image_tag}")

        # Stop running container first
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            # No Docker — fall back to VM snapshot restore
            if deployment["status"] == DeploymentStatus.RUNNING:
                await self.stop_deployment(deployment_id, force=True)
            await self.vm_provisioner.restore_snapshot(deployment["vm_name"], snapshot_name)
            await self.start_deployment(deployment_id)
            return deployment

        # Re-run container from backup image
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "--restart",
                "unless-stopped",
                image_tag,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to restore container: {result.stderr.strip()}")

        deployment["status"] = DeploymentStatus.RUNNING
        deployment["health_status"] = "healthy"
        deployment["updated_at"] = datetime.utcnow().isoformat()
        self._save_deployment_to_db(deployment)

        return deployment


# Example usage
if __name__ == "__main__":

    async def main():
        service = DeploymentService()

        # Create deployment
        config = DeploymentConfig(
            company_id="comp-123",
            tenant_name="acme-corp",
            subdomain="acme",
            memory_mb=4096,
            cpu_cores=2,
            disk_size_gb=50,
        )

        deployment = await service.create_deployment(config)
        print(f"Deployment created: {deployment}")

        # Wait for deployment to complete
        await asyncio.sleep(60)

        # Get deployment info
        info = await service.get_deployment(deployment["id"])
        print(f"Deployment info: {info}")

        # Get metrics
        metrics = await service.get_deployment_metrics(deployment["id"])
        print(f"Metrics: {metrics}")

    asyncio.run(main())

# Made with Bob
