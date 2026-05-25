"""
Role-based access control (RBAC) and permissions
"""
from enum import Enum
from typing import List
from fastapi import HTTPException, status


class Role(str, Enum):
    """User roles"""
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class Permission(str, Enum):
    """System permissions"""
    # User permissions
    READ_OWN_DATA = "read:own_data"
    WRITE_OWN_DATA = "write:own_data"
    DELETE_OWN_DATA = "delete:own_data"
    
    # Company permissions
    CREATE_COMPANY = "create:company"
    READ_COMPANY = "read:company"
    UPDATE_COMPANY = "update:company"
    DELETE_COMPANY = "delete:company"
    
    # Deployment permissions
    CREATE_DEPLOYMENT = "create:deployment"
    READ_DEPLOYMENT = "read:deployment"
    UPDATE_DEPLOYMENT = "update:deployment"
    DELETE_DEPLOYMENT = "delete:deployment"
    
    # Admin permissions
    READ_ALL_USERS = "read:all_users"
    UPDATE_ANY_USER = "update:any_user"
    DELETE_ANY_USER = "delete:any_user"
    READ_ALL_COMPANIES = "read:all_companies"
    READ_ALL_DEPLOYMENTS = "read:all_deployments"
    
    # System permissions
    MANAGE_SYSTEM = "manage:system"
    VIEW_ANALYTICS = "view:analytics"
    MANAGE_BILLING = "manage:billing"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.READ_OWN_DATA,
        Permission.WRITE_OWN_DATA,
        Permission.DELETE_OWN_DATA,
        Permission.CREATE_COMPANY,
        Permission.READ_COMPANY,
        Permission.UPDATE_COMPANY,
        Permission.DELETE_COMPANY,
        Permission.CREATE_DEPLOYMENT,
        Permission.READ_DEPLOYMENT,
        Permission.UPDATE_DEPLOYMENT,
        Permission.DELETE_DEPLOYMENT,
    ],
    Role.ADMIN: [
        # All user permissions
        Permission.READ_OWN_DATA,
        Permission.WRITE_OWN_DATA,
        Permission.DELETE_OWN_DATA,
        Permission.CREATE_COMPANY,
        Permission.READ_COMPANY,
        Permission.UPDATE_COMPANY,
        Permission.DELETE_COMPANY,
        Permission.CREATE_DEPLOYMENT,
        Permission.READ_DEPLOYMENT,
        Permission.UPDATE_DEPLOYMENT,
        Permission.DELETE_DEPLOYMENT,
        # Admin-specific permissions
        Permission.READ_ALL_USERS,
        Permission.READ_ALL_COMPANIES,
        Permission.READ_ALL_DEPLOYMENTS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_BILLING,
    ],
    Role.SUPERADMIN: [
        # All permissions
        *[p for p in Permission]
    ]
}


def get_role_permissions(role: Role) -> List[Permission]:
    """
    Get all permissions for a role
    
    Args:
        role: User role
        
    Returns:
        List of permissions
    """
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user_role: str, required_permission: Permission) -> bool:
    """
    Check if a user role has a specific permission
    
    Args:
        user_role: User's role
        required_permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    try:
        role = Role(user_role)
        permissions = get_role_permissions(role)
        return required_permission in permissions
    except ValueError:
        return False


def check_permission(user_role: str, required_permission: Permission):
    """
    Check permission and raise exception if not authorized
    
    Args:
        user_role: User's role
        required_permission: Permission to check
        
    Raises:
        HTTPException: If user doesn't have permission
    """
    if not has_permission(user_role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required_permission.value} required"
        )


def require_role(required_role: Role):
    """
    Decorator to require a specific role
    
    Args:
        required_role: Minimum required role
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get("current_user")
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_role = Role(current_user.get("role", "user"))
            
            # Check if user has required role or higher
            role_hierarchy = [Role.USER, Role.ADMIN, Role.SUPERADMIN]
            user_level = role_hierarchy.index(user_role)
            required_level = role_hierarchy.index(required_role)
            
            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {required_role.value} or higher required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def can_access_resource(user_id: str, resource_owner_id: str, user_role: str) -> bool:
    """
    Check if user can access a resource
    
    Args:
        user_id: Current user's ID
        resource_owner_id: Resource owner's ID
        user_role: Current user's role
        
    Returns:
        True if user can access, False otherwise
    """
    # User can access their own resources
    if user_id == resource_owner_id:
        return True
    
    # Admins and superadmins can access all resources
    if user_role in [Role.ADMIN.value, Role.SUPERADMIN.value]:
        return True
    
    return False


def filter_sensitive_data(data: dict, user_role: str) -> dict:
    """
    Filter sensitive data based on user role
    
    Args:
        data: Data dictionary
        user_role: User's role
        
    Returns:
        Filtered data dictionary
    """
    # Superadmins see everything
    if user_role == Role.SUPERADMIN.value:
        return data
    
    # Remove sensitive fields for non-superadmins
    sensitive_fields = ["password_hash", "api_keys", "secrets"]
    filtered = data.copy()
    
    for field in sensitive_fields:
        if field in filtered:
            del filtered[field]
    
    return filtered

# Made with Bob
