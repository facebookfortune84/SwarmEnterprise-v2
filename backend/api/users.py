"""
User management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.auth.user_service import UserService, UserUpdate, UserResponse
from backend.auth.middleware import get_current_active_user, get_current_admin_user
from backend.auth.permissions import can_access_resource
from backend.db.session import get_db
from backend.db.models import User


router = APIRouter(prefix="/api/users", tags=["users"])


class UserUpdateRequest(BaseModel):
    """User update request schema"""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """
    Get current user's profile
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(current_user["id"])

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_service.to_response(user)


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's profile
    """
    user_service = UserService(db)
    update_data = UserUpdate(**user_data.model_dump(exclude_unset=True))
    updated_user = user_service.update_user(current_user["id"], update_data)

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_service.to_response(updated_user)


@router.delete("/me")
async def delete_my_account(
    current_user: dict = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """
    Delete current user's account (soft delete)
    """
    user_service = UserService(db)
    success = user_service.delete_user(current_user["id"])

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"message": "Account deleted successfully"}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get user by ID (admin only or own profile)
    """
    user_service = UserService(db)
    # Check if user can access this resource
    if not can_access_resource(current_user["id"], user_id, current_user["role"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user"
        )

    user = user_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_service.to_response(user)


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    List all users (admin only)
    """
    users = db.query(User).offset(skip).limit(limit).all()
    user_service = UserService(db)
    return [user_service.to_response(user) for user in users]


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    current_user: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Update user by ID (admin only)
    """
    user_service = UserService(db)
    update_data = UserUpdate(**user_data.model_dump(exclude_unset=True))
    updated_user = user_service.update_user(user_id, update_data)

    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_service.to_response(updated_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete user by ID (admin only)
    """
    user_service = UserService(db)
    success = user_service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"message": "User deleted successfully"}


@router.post("/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Suspend user account (admin only)
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()

    return {"message": "User suspended successfully"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Activate suspended user account (admin only)
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()

    return {"message": "User activated successfully"}


# Made with Bob
