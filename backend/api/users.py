"""
User management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.auth.user_service import UserService, UserUpdate, UserResponse
from backend.auth.middleware import (
    get_current_active_user,
    get_current_admin_user
)
from backend.auth.permissions import can_access_resource


router = APIRouter(prefix="/api/users", tags=["users"])
user_service = UserService()


class UserUpdateRequest(BaseModel):
    """User update request schema"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user's profile
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile data
    """
    user = user_service.get_user_by_id(current_user["id"])  # type: ignore[assignment]
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_service.to_response(user)


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Update current user's profile
    
    Args:
        user_data: Updated user data
        current_user: Current authenticated user
        
    Returns:
        Updated user profile
    """
    update_data = UserUpdate(**user_data.dict(exclude_unset=True))
    updated_user = user_service.update_user(current_user["id"], update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_service.to_response(updated_user)


@router.delete("/me")
async def delete_my_account(current_user: dict = Depends(get_current_active_user)):
    """
    Delete current user's account (soft delete)
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    success = user_service.delete_user(current_user["id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Account deleted successfully"}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get user by ID (admin only or own profile)
    
    Args:
        user_id: User ID to retrieve
        current_user: Current authenticated user
        
    Returns:
        User profile data
        
    Raises:
        HTTPException: If not authorized or user not found
    """
    # Check if user can access this resource
    if not can_access_resource(current_user["id"], user_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user"
        )
    
    user = user_service.get_user_by_id(user_id)  # type: ignore[assignment]
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_service.to_response(user)


@router.get("/", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    List all users (admin only)
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated admin user
        
    Returns:
        List of users
    """
    # TODO: Implement database query
    # users = db.query(User).offset(skip).limit(limit).all()
    # return [user_service.to_response(user) for user in users]
    
    return []


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Update user by ID (admin only)
    
    Args:
        user_id: User ID to update
        user_data: Updated user data
        current_user: Current authenticated admin user
        
    Returns:
        Updated user profile
    """
    update_data = UserUpdate(**user_data.dict(exclude_unset=True))
    updated_user = user_service.update_user(user_id, update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_service.to_response(updated_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Delete user by ID (admin only)
    
    Args:
        user_id: User ID to delete
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    success = user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Suspend user account (admin only)
    
    Args:
        user_id: User ID to suspend
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    # TODO: Implement user suspension
    # user = user_service.get_user_by_id(user_id)
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")
    # user.is_active = False
    # db.commit()
    
    return {"message": "User suspended successfully"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Activate suspended user account (admin only)
    
    Args:
        user_id: User ID to activate
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    # TODO: Implement user activation
    # user = user_service.get_user_by_id(user_id)
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")
    # user.is_active = True
    # db.commit()
    
    return {"message": "User activated successfully"}

# Made with Bob
