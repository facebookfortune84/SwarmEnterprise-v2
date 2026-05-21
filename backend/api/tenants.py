"""Multi-tenant company box API."""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.core.tenants import tenant_service

router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


class RegisterTenantRequest(BaseModel):
    name: str
    slug: str | None = None


class ProvisionRequest(BaseModel):
    use_vm: bool = False


@router.post("/register")
def register_tenant(body: RegisterTenantRequest):
    tenant = tenant_service.register(body.name, body.slug)
    return {"status": "registered", "tenant": tenant}


@router.get("")
def list_tenants():
    return {"tenants": tenant_service.list_tenants()}


@router.get("/{tenant_id}")
def get_tenant(tenant_id: str):
    tenant = tenant_service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/{tenant_id}/provision")
def provision_tenant(tenant_id: str, body: ProvisionRequest, background_tasks: BackgroundTasks):
    tenant = tenant_service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    def _run():
        tenant_service.provision(tenant_id, use_vm=body.use_vm)

    background_tasks.add_task(_run)
    return {"status": "provisioning_started", "tenant_id": tenant_id}


@router.post("/{tenant_id}/provision-sync")
def provision_tenant_sync(tenant_id: str, body: ProvisionRequest):
    """Synchronous provision for scripts/tests."""
    tenant = tenant_service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = tenant_service.provision(tenant_id, use_vm=body.use_vm)
    return {"status": "done", "tenant": result}


@router.get("/{tenant_id}/status")
def tenant_status(tenant_id: str):
    tenant = tenant_service.refresh_status(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
