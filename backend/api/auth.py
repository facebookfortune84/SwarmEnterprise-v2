"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from backend.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    refresh_access_token
)
from backend.auth.user_service import UserService, UserCreate, UserResponse
from backend.auth.middleware import get_current_user, get_current_active_user
from backend.db.session import get_db


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    """Token refresh request schema"""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Token refresh response schema"""
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequest(BaseModel):
    """Password reset request schema"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema"""
    token: str
    new_password: str


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    user_service = UserService(db)
    # Check if user already exists
    existing_user = user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = user_service.create_user(user_data)
    
    # Generate tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_service.to_response(user)
    )


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password
    """
    user_service = UserService(db)
    # Authenticate user
    user = user_service.authenticate_user(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role
    }
    access_token = create_access_token(token_data)
    refresh_token_str = create_refresh_token(token_data)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        user=user_service.to_response(user)
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout current user (revoke token)
    """
    # TODO: Implement token revocation with Redis
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: RefreshRequest):
    """
    Refresh access token using refresh token
    """
    new_access_token = refresh_access_token(request.refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return RefreshResponse(access_token=new_access_token)


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_active_user)):
    """
    Verify current token and return user info
    """
    return {
        "valid": True,
        "user": current_user
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get current user information
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(current_user["id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_service.to_response(user)

# Made with Bob
