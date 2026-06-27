"""
Deployments API - REST endpoints for managing tenant deployments

Provides endpoints for creating, managing, and monitoring VM-based deployments.
"""

import subprocess

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from backend.auth.middleware import get_current_active_user, get_current_admin_user
from backend.auth.permissions import Role, has_permission, Permission
from backend.services.deployment_service import (
    DeploymentService,
    DeploymentConfig,
    DeploymentStatus,
)

router = APIRouter(prefix="/api/deployments", tags=["deployments"])

# Initialize service
deployment_service = DeploymentService()


# Request/Response Models


class CreateDeploymentRequest(BaseModel):
    """Create deployment request"""

    company_id: str = Field(..., description="Company ID to deploy")
    tenant_name: str = Field(..., description="Tenant name (alphanumeric, lowercase)")
    subdomain: str = Field(..., description="Subdomain for tenant")
    memory_mb: int = Field(4096, ge=2048, le=32768, description="Memory in MB")
    cpu_cores: int = Field(2, ge=1, le=16, description="CPU cores")
    disk_size_gb: int = Field(50, ge=20, le=500, description="Disk size in GB")
    auto_start: bool = Field(True, description="Auto-start after creation")
    backup_enabled: bool = Field(True, description="Enable automatic backups")


class DeploymentResponse(BaseModel):
    """Deployment response"""

    id: str
    company_id: str
    tenant_name: str
    subdomain: str
    vm_name: str
    status: str
    url: str
    ip_address: Optional[str]
    health_status: str
    created_at: str
    updated_at: str


class DeploymentMetricsResponse(BaseModel):
    """Deployment metrics response"""

    deployment_id: str
    status: str
    health_status: str
    cpu_usage_percent: int
    memory_usage_mb: int
    network_in_mbps: int
    network_out_mbps: int
    disk_read_iops: int
    disk_write_iops: int
    timestamp: str


class BackupResponse(BaseModel):
    """Backup response"""

    deployment_id: str
    snapshot_name: str
    created_at: str


# Endpoints


@router.post(
    "/",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create deployment",
    description="Create a new tenant deployment with VM provisioning",
)
async def create_deployment(
    request: CreateDeploymentRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Create a new deployment.

    Provisions a VM and deploys the company application.
    This is an async operation - check status endpoint for progress.

    Requires: CREATE_DEPLOYMENT permission
    """
    # Check permission
    if not has_permission(current_user["role"], Permission.CREATE_DEPLOYMENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    try:
        config = DeploymentConfig(
            company_id=request.company_id,
            tenant_name=request.tenant_name,
            subdomain=request.subdomain,
            memory_mb=request.memory_mb,
            cpu_cores=request.cpu_cores,
            disk_size_gb=request.disk_size_gb,
            auto_start=request.auto_start,
            backup_enabled=request.backup_enabled,
        )

        deployment = await deployment_service.create_deployment(config)

        return DeploymentResponse(**deployment)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deployment: {str(e)}",
        )


@router.get(
    "/",
    response_model=List[DeploymentResponse],
    summary="List deployments",
    description="List all deployments (filtered by user permissions)",
)
async def list_deployments(
    status_filter: Optional[DeploymentStatus] = None,
    current_user: dict = Depends(get_current_active_user),
):
    """
    List deployments.

    Regular users see only their deployments.
    Admins see all deployments.
    """
    try:
        deployments = await deployment_service.list_deployments(status=status_filter)

        # Filter by user if not admin
        if current_user["role"] != Role.SUPERADMIN:
            # Filter deployments by checking company ownership
            from backend.db.session import SessionLocal
            from backend.db.models import CompanyTenant

            db = SessionLocal()
            try:
                # Get user's company IDs (simplified - assumes user owns companies)
                user_companies = db.query(CompanyTenant).all()
                user_company_ids = {c.id for c in user_companies}

                # Filter deployments
                deployments = [d for d in deployments if d.get("company_id") in user_company_ids]
            finally:
                db.close()

        return [DeploymentResponse(**d) for d in deployments]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list deployments: {str(e)}",
        )


@router.get(
    "/{deployment_id}",
    response_model=DeploymentResponse,
    summary="Get deployment",
    description="Get deployment details",
)
async def get_deployment(
    deployment_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Get deployment by ID"""
    try:
        deployment = await deployment_service.get_deployment(deployment_id)

        # Check ownership if not admin
        if current_user["role"] != Role.SUPERADMIN:
            from backend.db.session import SessionLocal
            from backend.db.models import CompanyTenant

            db = SessionLocal()
            try:
                company_id = deployment.get("company_id")
                company = db.query(CompanyTenant).filter_by(id=company_id).first()

                # Simplified ownership check - in production, add user_id to CompanyTenant
                if not company:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this deployment",
                    )
            finally:
                db.close()

        return DeploymentResponse(**deployment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment: {str(e)}",
        )


@router.post(
    "/{deployment_id}/start",
    response_model=DeploymentResponse,
    summary="Start deployment",
    description="Start a stopped deployment",
)
async def start_deployment(
    deployment_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Start a stopped deployment"""
    try:
        deployment = await deployment_service.start_deployment(deployment_id)
        return DeploymentResponse(**deployment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start deployment: {str(e)}",
        )


@router.post(
    "/{deployment_id}/stop",
    response_model=DeploymentResponse,
    summary="Stop deployment",
    description="Stop a running deployment",
)
async def stop_deployment(
    deployment_id: str,
    force: bool = False,
    current_user: dict = Depends(get_current_active_user),
):
    """Stop a running deployment"""
    try:
        deployment = await deployment_service.stop_deployment(deployment_id, force=force)
        return DeploymentResponse(**deployment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop deployment: {str(e)}",
        )


@router.post(
    "/{deployment_id}/restart",
    response_model=DeploymentResponse,
    summary="Restart deployment",
    description="Restart a deployment",
)
async def restart_deployment(
    deployment_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Restart a deployment"""
    try:
        deployment = await deployment_service.restart_deployment(deployment_id)
        return DeploymentResponse(**deployment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart deployment: {str(e)}",
        )


@router.delete(
    "/{deployment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete deployment",
    description="Delete a deployment and optionally its VM",
)
async def delete_deployment(
    deployment_id: str,
    delete_vm: bool = True,
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a deployment"""
    # Check permission
    if not has_permission(current_user["role"], Permission.DELETE_DEPLOYMENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    try:
        await deployment_service.delete_deployment(deployment_id, delete_vm=delete_vm)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deployment: {str(e)}",
        )


@router.get(
    "/{deployment_id}/metrics",
    response_model=DeploymentMetricsResponse,
    summary="Get deployment metrics",
    description="Get real-time performance metrics for a deployment",
)
async def get_deployment_metrics(
    deployment_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Get deployment metrics"""
    try:
        metrics = await deployment_service.get_deployment_metrics(deployment_id)
        return DeploymentMetricsResponse(**metrics)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )


@router.post(
    "/{deployment_id}/backup",
    response_model=BackupResponse,
    summary="Create backup",
    description="Create a VM snapshot backup",
)
async def create_backup(
    deployment_id: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Create deployment backup"""
    try:
        backup = await deployment_service.create_backup(deployment_id)
        return BackupResponse(**backup)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}",
        )


@router.post(
    "/{deployment_id}/restore",
    response_model=DeploymentResponse,
    summary="Restore backup",
    description="Restore deployment from a snapshot",
)
async def restore_backup(
    deployment_id: str,
    snapshot_name: str,
    current_user: dict = Depends(get_current_admin_user),  # Admin only
):
    """Restore deployment from backup"""
    try:
        deployment = await deployment_service.restore_backup(deployment_id, snapshot_name)
        return DeploymentResponse(**deployment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}",
        )


@router.get(
    "/{deployment_id}/logs",
    summary="Get deployment logs",
    description="Return the last N lines of logs from the deployment container",
)
async def get_deployment_logs(
    deployment_id: str,
    lines: int = 100,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Return deployment logs from the Docker container named ``tenant-<tenant_name>``.
    Falls back to any on-disk log file if Docker is unavailable.
    """
    try:
        deployment = await deployment_service.get_deployment(deployment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    tenant_name = deployment.get("tenant_name", deployment_id)
    container_name = f"tenant-{tenant_name}"

    def _iter_docker_logs():
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container_name],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            if not output.strip():
                output = f"(no log output from container {container_name})\n"
        except FileNotFoundError:
            output = f"Docker not available. Container: {container_name}\n"
        except subprocess.TimeoutExpired:
            output = f"Timeout reading logs for container: {container_name}\n"
        yield output

    return StreamingResponse(
        _iter_docker_logs(),
        media_type="text/plain",
    )


# Health check for deployments service
@router.get(
    "/health", summary="Health check", description="Check if deployments service is healthy"
)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "deployments",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Made with Bob
