"""
Company fixtures for testing
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional


def create_test_company(
    name: str = "Test Company",
    slug: str = "test-company",
    user_id: Optional[str] = None,
    tech_stack: str = "fastapi-react-postgres",
    status: str = "pending",
    **kwargs
) -> Dict[str, Any]:
    """Create a test company object"""
    company_id = kwargs.get("id", str(uuid.uuid4()))
    return {
        "id": company_id,
        "user_id": user_id or str(uuid.uuid4()),
        "name": name,
        "slug": slug,
        "description": kwargs.get("description", f"Test description for {name}"),
        "tech_stack": tech_stack,
        "status": status,
        "template_id": kwargs.get("template_id", tech_stack),
        "generation_started_at": kwargs.get("generation_started_at"),
        "generation_completed_at": kwargs.get("generation_completed_at"),
        "download_count": kwargs.get("download_count", 0),
        "storage_path": kwargs.get("storage_path", f"companies/{company_id}/source.zip"),
        "metadata": kwargs.get("metadata", {}),
        "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
    }


def create_completed_company(**kwargs) -> Dict[str, Any]:
    """Create a test company with completed status"""
    now = datetime.utcnow()
    return create_test_company(
        status="completed",
        generation_started_at=kwargs.get("generation_started_at", now.isoformat()),
        generation_completed_at=kwargs.get("generation_completed_at", now.isoformat()),
        **kwargs
    )


def create_failed_company(**kwargs) -> Dict[str, Any]:
    """Create a test company with failed status"""
    return create_test_company(
        status="failed",
        **kwargs
    )


# Sample test companies
TEST_COMPANIES = {
    "pending": create_test_company(),
    "completed": create_completed_company(name="Completed Company", slug="completed-company"),
    "failed": create_failed_company(name="Failed Company", slug="failed-company"),
}

# Made with Bob
