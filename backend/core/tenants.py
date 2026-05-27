"""Tenant registry and provisioning orchestration."""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.db.models import CompanyTenant
from backend.db.session import SessionLocal, engine
from backend.orchestration.box_deployer import BoxDeployer, _slugify

logger = logging.getLogger("tenants")


class TenantService:
    def __init__(self, db: Optional[Session] = None):
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
            if not self.db: # Only close if we created it
                 self.db.close()

    def list_tenants(self) -> List[CompanyTenant]:
        return self.db.query(CompanyTenant).order_by(CompanyTenant.created_at.desc()).all()

    def get(self, tenant_id: str) -> Optional[CompanyTenant]:
        return self.db.query(CompanyTenant).filter_by(id=tenant_id).first()

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

            deploy = self.deployer.deploy_docker_box(tenant.slug, tenant.id)
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
