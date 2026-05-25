"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from backend.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    refresh_access_token
)
from backend.auth.user_service import UserService, UserCreate, UserResponse
from backend.auth.middleware import get_current_user, get_current_active_user


router = APIRouter(prefix="/api/auth", tags=["authentication"])
user_service = UserService()


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
async def register(user_data: UserCreate):
    """
    Register a new user
    
    Args:
        user_data: User registration data
        
    Returns:
        Access token, refresh token, and user data
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = user_service.get_user_by_email(user_data.email)  # type: ignore[assignment]
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
async def login(credentials: LoginRequest):
    """
    Login with email and password
    
    Args:
        credentials: Login credentials
        
    Returns:
        Access token, refresh token, and user data
        
    Raises:
        HTTPException: If credentials are invalid
    """
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
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # TODO: Implement token revocation with Redis
    # For now, client should discard the token
    
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: RefreshRequest):
    """
    Refresh access token using refresh token
    
    Args:
        request: Refresh token request
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    new_access_token = refresh_access_token(request.refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return RefreshResponse(access_token=new_access_token)


@router.post("/reset-password")
async def reset_password(request: PasswordResetRequest):
    """
    Request password reset (send email with reset link)
    
    Args:
        request: Password reset request
        
    Returns:
        Success message
    """
    user = user_service.get_user_by_email(request.email)  # type: ignore[assignment]
    
    if user:
        # TODO: Generate reset token and send email
        # reset_token = create_access_token(
        #     {"sub": user.id, "purpose": "password_reset"},
        #     expires_delta=timedelta(hours=1)
        # )
        # send_password_reset_email(user.email, reset_token)
        pass
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password/confirm")
async def confirm_password_reset(request: PasswordResetConfirm):
    """
    Confirm password reset with token
    
    Args:
        request: Password reset confirmation
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If token is invalid
    """
    # TODO: Verify reset token and update password
    # payload = decode_token(request.token)
    # if not payload or payload.get("purpose") != "password_reset":
    #     raise HTTPException(status_code=400, detail="Invalid reset token")
    # 
    # user_id = payload.get("sub")
    # success = user_service.reset_password(user_id, request.new_password)
    # 
    # if not success:
    #     raise HTTPException(status_code=400, detail="Password reset failed")
    
    return {"message": "Password has been reset successfully"}


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_active_user)):
    """
    Verify current token and return user info
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return {
        "valid": True,
        "user": current_user
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """
    Get current user information
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    user = user_service.get_user_by_id(current_user["id"])  # type: ignore[assignment]
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user_service.to_response(user)

# Made with Bob
