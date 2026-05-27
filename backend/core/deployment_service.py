"""
Deployment service - manages the lifecycle and persistence of application deployments.
100% Operational, Zero-Cost FOSS implementation.
"""
import uuid
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.db.models import CompanyTenant, Deployment
from backend.db.session import SessionLocal
from agents.devops.infrastructure_agent import infra_agent

logger = logging.getLogger(__name__)


class DeploymentService:
    """
    Manages application deployments for tenants.
    Connects InfrastructureAgent actions with Database persistence.
    """
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()

    async def deploy_tenant_application(
        self, 
        tenant_id: str, 
        version: str = "1.0.0", 
        strategy: str = "rolling"
    ) -> Dict[str, Any]:
        """
        Executes a deployment for a specific tenant.
        """
        tenant = self.db.query(CompanyTenant).filter_by(id=tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Create Deployment record
        deployment = Deployment(
            id=f"DEP-{uuid.uuid4().hex[:8].upper()}",
            tenant_id=tenant_id,
            status="in_progress",
            strategy=strategy,
            version=version
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)

        try:
            # Trigger Infrastructure Agent
            # For 100% logic, we assume custom code is already generated in the tenant's slug dir
            app_source = f"./output/src/{tenant.slug}"
            
            result = await infra_agent.deploy_custom_app(
                tenant_id=tenant_id,
                slug=tenant.slug,
                app_source_path=app_source
            )

            if result.get("status") == "success" or result.get("status") == "running":
                deployment.status = "success"
                deployment.metadata_json = json.dumps(result)
                tenant.status = "running"
            else:
                deployment.status = "failed"
                deployment.metadata_json = json.dumps(result)
                tenant.last_error = result.get("error", "Deployment failed")
            
            self.db.commit()
            return result

        except Exception as e:
            logger.error(f"Deployment service failed for {tenant_id}: {e}")
            deployment.status = "failed"
            deployment.metadata_json = json.dumps({"error": str(e)})
            self.db.commit()
            return {"status": "failed", "error": str(e)}

    def get_deployment_history(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Returns deployment history for a tenant."""
        deployments = self.db.query(Deployment).filter_by(tenant_id=tenant_id).order_by(Deployment.created_at.desc()).all()
        return [
            {
                "id": d.id,
                "status": d.status,
                "strategy": d.strategy,
                "version": d.version,
                "created_at": d.created_at.isoformat(),
                "details": json.loads(d.metadata_json) if d.metadata_json else {}
            }
            for d in deployments
        ]

# Global instance
deployment_service = DeploymentService()
