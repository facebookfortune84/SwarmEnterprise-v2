"""Tenant registry and provisioning orchestration."""

import json
import logging
import os
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.tenant_models import CompanyTenant, TenantBase
from backend.orchestration.box_deployer import BoxDeployer, _slugify

logger = logging.getLogger("tenants")


def _db_url() -> str:
    url = os.getenv("SWARM_DB_URL")
    if url:
        return url
    db_dir = Path(os.getenv("SWARM_PG_DIR", Path(__file__).resolve().parents[2] / "pg_data"))
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(db_dir / 'swarm_tickets.db').as_posix()}"


class TenantService:
    def __init__(self):
        self.engine = create_engine(_db_url())
        TenantBase.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.deployer = BoxDeployer()

    def register(self, name: str, slug: str | None = None) -> CompanyTenant:
        session = self.Session()
        try:
            final_slug = _slugify(slug or name)
            existing = session.query(CompanyTenant).filter_by(slug=final_slug).first()
            if existing:
                return self._to_dict(existing)  # type: ignore[return-value]
            tenant = CompanyTenant(
                id=f"TEN-{uuid.uuid4().hex[:8].upper()}",
                slug=final_slug,
                name=name,
                subdomain=f"{final_slug}.{os.getenv('TECH_DOMAIN', 'realms2riches.tech')}",
                status="pending",
                box_url=f"https://{final_slug}.{os.getenv('TECH_DOMAIN', 'realms2riches.tech')}",
            )
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            data = self._to_dict(tenant)
            return data  # type: ignore[return-value]
        finally:
            session.close()

    def list_tenants(self) -> list[dict]:
        session = self.Session()
        try:
            rows = session.query(CompanyTenant).order_by(CompanyTenant.created_at.desc()).all()
            return [self._to_dict(r) for r in rows]
        finally:
            session.close()

    def get(self, tenant_id: str) -> dict | None:
        session = self.Session()
        try:
            row = session.query(CompanyTenant).filter_by(id=tenant_id).first()
            return self._to_dict(row) if row else None
        finally:
            session.close()

    def provision(self, tenant_id: str, use_vm: bool = False) -> dict:
        session = self.Session()
        try:
            tenant = session.query(CompanyTenant).filter_by(id=tenant_id).first()
            if not tenant:
                return {"error": "tenant not found"}
            tenant.status = "provisioning"
            session.commit()

            vm_result = None
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
            session.commit()
            return self._to_dict(tenant)
        finally:
            session.close()

    def refresh_status(self, tenant_id: str) -> dict | None:
        session = self.Session()
        try:
            tenant = session.query(CompanyTenant).filter_by(id=tenant_id).first()
            if not tenant:
                return None
            docker_status = self.deployer.box_status(tenant.slug)
            if docker_status.get("status") == "running":
                tenant.status = "running"
            elif docker_status.get("status") in ("exited", "dead"):
                tenant.status = "failed"
                tenant.last_error = f"container {docker_status.get('status')}"
            session.commit()
            out = self._to_dict(tenant)
            out["docker"] = docker_status
            return out
        finally:
            session.close()

    @staticmethod
    def _to_dict(row: CompanyTenant | None) -> dict | None:
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


tenant_service = TenantService()
