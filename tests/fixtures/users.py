"""
User fixtures for testing
"""
import uuid
from datetime import datetime
from typing import Dict, Any


def create_test_user(
    email: str = "test@example.com",
    full_name: str = "Test User",
    role: str = "user",
    subscription_tier: str = "free",
    **kwargs
) -> Dict[str, Any]:
    """Create a test user object"""
    user_id = kwargs.get("id", str(uuid.uuid4()))
    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "role": role,
        "subscription_tier": subscription_tier,
        "created_at": kwargs.get("created_at", datetime.utcnow().isoformat()),
        "updated_at": kwargs.get("updated_at", datetime.utcnow().isoformat()),
        **{k: v for k, v in kwargs.items() if k not in ["id", "created_at", "updated_at"]}
    }


def create_admin_user(**kwargs) -> Dict[str, Any]:
    """Create a test admin user"""
    return create_test_user(
        email=kwargs.get("email", "admin@example.com"),
        full_name=kwargs.get("full_name", "Admin User"),
        role="admin",
        **kwargs
    )


def create_premium_user(**kwargs) -> Dict[str, Any]:
    """Create a test premium user"""
    return create_test_user(
        email=kwargs.get("email", "premium@example.com"),
        full_name=kwargs.get("full_name", "Premium User"),
        subscription_tier="premium",
        **kwargs
    )


# Sample test users
TEST_USERS = {
    "basic": create_test_user(),
    "admin": create_admin_user(),
    "premium": create_premium_user(),
}

# Made with Bob
