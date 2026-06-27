"""
Custom assertions for testing
"""
from typing import Any, Dict, List, Optional


def assert_api_success(response: Dict[str, Any], expected_status: int = 200):
    """Assert API response is successful"""
    assert (
        response.get("status_code") == expected_status
    ), f"Expected status {expected_status}, got {response.get('status_code')}"


def assert_api_error(
    response: Dict[str, Any], expected_status: int, expected_message: Optional[str] = None
):
    """Assert API response is an error"""
    assert (
        response.get("status_code") == expected_status
    ), f"Expected status {expected_status}, got {response.get('status_code')}"

    if expected_message:
        detail = response.get("detail", "")
        assert expected_message in str(
            detail
        ), f"Expected message '{expected_message}' not found in '{detail}'"


def assert_has_fields(obj: Dict[str, Any], fields: List[str]):
    """Assert object has all specified fields"""
    missing = [f for f in fields if f not in obj]
    assert not missing, f"Missing required fields: {missing}"


def assert_valid_company(company: Dict[str, Any]):
    """Assert company object has valid structure"""
    required_fields = ["id", "name", "slug", "user_id", "tech_stack", "status", "created_at"]
    assert_has_fields(company, required_fields)

    # Validate status
    valid_statuses = ["pending", "in_progress", "completed", "failed"]
    assert company["status"] in valid_statuses, f"Invalid status: {company['status']}"

    # Validate tech_stack
    valid_stacks = ["fastapi-react-postgres", "nodejs-tailwind-mongo", "django-vue-mysql"]
    assert company["tech_stack"] in valid_stacks, f"Invalid tech_stack: {company['tech_stack']}"


def assert_valid_deployment(deployment: Dict[str, Any]):
    """Assert deployment object has valid structure"""
    required_fields = ["id", "company_id", "user_id", "subdomain", "status", "url", "created_at"]
    assert_has_fields(deployment, required_fields)

    # Validate status
    valid_statuses = ["pending", "provisioning", "active", "stopped", "failed"]
    assert deployment["status"] in valid_statuses, f"Invalid status: {deployment['status']}"

    # Validate URL format
    assert deployment["url"].startswith("https://"), f"Invalid URL format: {deployment['url']}"


def assert_valid_user(user: Dict[str, Any]):
    """Assert user object has valid structure"""
    required_fields = ["id", "email", "role", "subscription_tier", "created_at"]
    assert_has_fields(user, required_fields)

    # Validate email format
    assert "@" in user["email"], f"Invalid email: {user['email']}"

    # Validate role
    valid_roles = ["user", "admin", "superadmin"]
    assert user["role"] in valid_roles, f"Invalid role: {user['role']}"

    # Validate subscription tier
    valid_tiers = ["free", "basic", "premium", "enterprise"]
    assert (
        user["subscription_tier"] in valid_tiers
    ), f"Invalid subscription_tier: {user['subscription_tier']}"


def assert_valid_ticket(ticket: Dict[str, Any]):
    """Assert ticket object has valid structure"""
    required_fields = ["ticket_id", "department", "title", "instruction", "status", "priority"]
    assert_has_fields(ticket, required_fields)

    # Validate status
    valid_statuses = ["pending", "in_progress", "completed", "blocked"]
    assert ticket["status"] in valid_statuses, f"Invalid status: {ticket['status']}"

    # Validate priority
    valid_priorities = ["low", "medium", "high", "critical"]
    assert ticket["priority"] in valid_priorities, f"Invalid priority: {ticket['priority']}"


def assert_pagination(response: Dict[str, Any]):
    """Assert response has valid pagination structure"""
    required_fields = ["items", "total", "page", "page_size"]
    assert_has_fields(response, required_fields)

    assert isinstance(response["items"], list), "items must be a list"
    assert isinstance(response["total"], int), "total must be an integer"
    assert isinstance(response["page"], int), "page must be an integer"
    assert isinstance(response["page_size"], int), "page_size must be an integer"

    assert response["page"] > 0, "page must be positive"
    assert response["page_size"] > 0, "page_size must be positive"
    assert response["total"] >= 0, "total must be non-negative"
    assert len(response["items"]) <= response["page_size"], "items count exceeds page_size"


# Made with Bob
