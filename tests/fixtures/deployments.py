"""
Deployment fixtures for testing
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional


def create_test_deployment(
    company_id: Optional[str] = None,
    user_id: Optional[str] = None,
    subdomain: str = "test-deployment",
    status: str = "pending",
    **kwargs
) -> Dict[str, Any]:
    """Create a test deployment object"""
    deployment_id = kwargs.get("id", str(uuid.uuid4()))
    return {
        "id": deployment_id,
        "company_id": company_id or str(uuid.uuid4()),
        "user_id": user_id or str(uuid.uuid4()),
        "vm_id": kwargs.get("vm_id"),
        "container_id": kwargs.get("container_id"),
        "subdomain": subdomain,
        "status": status,
        "url": kwargs.get("url", f"https://{subdomain}.realms2riches.tech"),
        "resources": kwargs.get("resources", {
            "cpu": "2",
            "memory": "4GB",
            "disk": "50GB"
        }),
        "last_health_check": kwargs.get("last_health_check"),
        "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
        "updated_at": kwargs.get("updated_at", datetime.utcnow().isoformat()),
    }


def create_active_deployment(**kwargs) -> Dict[str, Any]:
    """Create a test deployment with active status"""
    return create_test_deployment(
        status="active",
        vm_id=kwargs.get("vm_id", "vm-12345"),
        container_id=kwargs.get("container_id", "container-67890"),
        last_health_check=kwargs.get("last_health_check", datetime.utcnow().isoformat()),
        **kwargs
    )


def create_failed_deployment(**kwargs) -> Dict[str, Any]:
    """Create a test deployment with failed status"""
    return create_test_deployment(
        status="failed",
        **kwargs
    )


# Sample test deployments
TEST_DEPLOYMENTS = {
    "pending": create_test_deployment(),
    "active": create_active_deployment(subdomain="active-deployment"),
    "failed": create_failed_deployment(subdomain="failed-deployment"),
}

# Made with Bob
