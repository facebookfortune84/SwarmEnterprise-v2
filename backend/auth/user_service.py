"""
User service for authentication and user management
"""
from datetime import datetime
from typing import Optional
import bcrypt
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from sqlalchemy.orm import Session
from backend.db.models import User


class UserCreate(BaseModel):
    """Schema for user creation"""

    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    """Schema for user updates"""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """User model for API responses (without password)"""

    id: str
    email: str
    full_name: str
    role: str
    subscription_tier: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """User model as stored in DB (with password hash)"""

    password_hash: str


class UserService:
    """Service for user management operations"""

    def __init__(self, db: Session):
        """
        Initialize user service

        Args:
            db: Database session
        """
        self.db = db

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user

        Args:
            user_data: User creation data

        Returns:
            Created user object
        """
        user = User(
            email=user_data.email,
            password_hash=self.hash_password(user_data.password),
            full_name=user_data.full_name,
            role="user",
            subscription_tier="free",
            is_active=True,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address

        Args:
            email: User email

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password

        Args:
            email: User email
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.get_user_by_email(email)

        if not user:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information

        Args:
            user_id: User ID
            user_data: Updated user data

        Returns:
            Updated user object or None if not found
        """
        user = self.get_user_by_id(user_id)

        if not user:
            return None

        # Update fields
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.email is not None:
            user.email = user_data.email

        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)

        return user

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user (soft delete by setting is_active=False)

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        user = self.get_user_by_id(user_id)

        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.utcnow()

        self.db.commit()

        return True

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """
        Reset user password

        Args:
            user_id: User ID
            new_password: New plain text password

        Returns:
            True if successful, False if user not found
        """
        user = self.get_user_by_id(user_id)

        if not user:
            return False

        user.password_hash = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()

        self.db.commit()

        return True

    def to_response(self, user: User) -> UserResponse:
        """
        Convert User (DB model) to UserResponse (Pydantic model)

        Args:
            user: User object from database

        Returns:
            User response object without password
        """
        return UserResponse.from_orm(user)


# Made with Bob
