"""
Authentication and authorization module for SwarmEnterprise
"""
from .jwt_handler import create_access_token, verify_token, decode_token
from .user_service import UserService
from .permissions import check_permission, require_role

__all__ = [
    "create_access_token",
    "verify_token",
    "decode_token",
    "UserService",
    "check_permission",
    "require_role",
]

# Made with Bob
