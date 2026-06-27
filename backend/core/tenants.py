"""Tenant registry and provisioning orchestration."""

import json
import logging
import os
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.db.models import CompanyTenant
from backend.db.session import SessionLocal
from backend.orchestration.box_deployer import BoxDeployer, _slugify

logger = logging.getLogger("tenants")


class TenantService:
    def __init__(self, db: Optional[Session] = None):
        self._owns_db = db is None  # track whether we created the session
        self.db = db or SessionLocal()
        self.deployer = BoxDeployer()

    def register(self, name: str, slug: str | None = None) -> CompanyTenant:
        try:
            final_slug = _slugify(slug or name)
            existing = self.db.query(CompanyTenant).filter_by(slug=final_slug).first()
            if existing:
                return existing
            tenant = CompanyTenant(
                id=f"TEN-{uuid.uuid4().hex[:8].upper()}",
                slug=final_slug,
                name=name,
                subdomain=f"{final_slug}.{os.getenv('TECH_DOMAIN', 'realms2riches.tech')}",
                status="pending",
                box_url=f"https://{final_slug}.{os.getenv('TECH_DOMAIN', 'realms2riches.tech')}",
            )
            self.db.add(tenant)
            self.db.commit()
            self.db.refresh(tenant)
            return tenant
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to register tenant: {e}")
            raise
        finally:
            if self._owns_db:  # Only close if we created the session
                self.db.close()

    def list_tenants(self) -> List[CompanyTenant]:
        return self.db.query(CompanyTenant).order_by(CompanyTenant.created_at.desc()).all()

    def get(self, tenant_id: str) -> Optional[CompanyTenant]:
        return self.db.query(CompanyTenant).filter_by(id=tenant_id).first()

    def _deploy_docker_fallback(self, tenant: CompanyTenant) -> dict:
        """
        Docker-based fallback when BoxDeployer is unavailable.
        Creates a named container for the tenant using the local Docker CLI.
        """
        import subprocess

        container_name = f"tenant-{tenant.slug}"
        image = os.getenv("DEPLOY_DOCKER_IMAGE", "nginx:alpine")
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
                    f"swarm.tenant_id={tenant.id}",
                    "-l",
                    f"swarm.slug={tenant.slug}",
                    image,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                container_id = result.stdout.strip()
                logger.info(
                    f"Fallback Docker container created: {container_name} ({container_id[:12]})"
                )
                return {
                    "status": "running",
                    "container_id": container_id[:12],
                    "box_url": tenant.box_url,
                }
            # Container may already exist — try starting it
            start = subprocess.run(
                ["docker", "start", container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if start.returncode == 0:
                # Get the container ID
                inspect = subprocess.run(
                    ["docker", "inspect", "--format", "{{.Id}}", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                cid = inspect.stdout.strip()[:12] if inspect.returncode == 0 else container_name
                return {"status": "running", "container_id": cid, "box_url": tenant.box_url}
            return {"status": "failed", "error": result.stderr.strip() or start.stderr.strip()}
        except FileNotFoundError:
            return {"status": "failed", "error": "Docker CLI not available"}
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Docker command timed out"}

    def provision(self, tenant_id: str, use_vm: bool = False) -> CompanyTenant:
        tenant = self.get(tenant_id)
        if not tenant:
            raise ValueError("tenant not found")

        tenant.status = "provisioning"
        self.db.commit()

        vm_result = None
        try:
            if use_vm:
                vm_result = self.deployer.provision_hyperv_vm(tenant.id, f"r2r-{tenant.slug}")

            try:
                deploy = self.deployer.deploy_docker_box(tenant.slug, tenant.id)
            except Exception as deployer_exc:
                logger.warning(
                    f"BoxDeployer.deploy_docker_box failed ({deployer_exc}); using Docker fallback"
                )
                deploy = self._deploy_docker_fallback(tenant)

            if deploy.get("status") == "running":
                tenant.status = "running"
                tenant.container_id = deploy.get("container_id")
                tenant.box_url = deploy.get("box_url", tenant.box_url)
                tenant.last_error = None
            else:
                tenant.status = "failed"
                tenant.last_error = deploy.get("error", "deploy failed")

            meta = {"vm": vm_result, "docker": deploy}
            tenant.metadata_json = json.dumps(meta)
            self.db.commit()
            self.db.refresh(tenant)
            return tenant
        except Exception as e:
            tenant.status = "failed"
            tenant.last_error = str(e)
            self.db.commit()
            raise

    def refresh_status(self, tenant_id: str) -> Optional[CompanyTenant]:
        tenant = self.get(tenant_id)
        if not tenant:
            return None

        docker_status = self.deployer.box_status(tenant.slug)
        if docker_status.get("status") == "running":
            tenant.status = "running"
        elif docker_status.get("status") in ("exited", "dead"):
            tenant.status = "failed"
            tenant.last_error = f"container {docker_status.get('status')}"

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def _to_dict(self, row: CompanyTenant | None) -> dict | None:
        """Kept for backward compatibility if needed, but prefer using the model directly."""
        if not row:
            return None
        return {
            "id": row.id,
            "slug": row.slug,
            "name": row.name,
            "subdomain": row.subdomain,
            "status": row.status,
            "vm_id": row.vm_id,
            "container_id": row.container_id,
            "box_url": row.box_url,
            "last_error": row.last_error,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


# Global instance (optional, but keep for compatibility)
tenant_service = TenantService()
