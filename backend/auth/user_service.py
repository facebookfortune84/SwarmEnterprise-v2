"""
User service for authentication and user management
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import bcrypt
from pydantic import BaseModel, EmailStr, validator


class UserCreate(BaseModel):
    """Schema for user creation"""
    email: EmailStr
    password: str
    full_name: str
    
    @validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseModel):
    """Schema for user updates"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserInDB(BaseModel):
    """User model as stored in database"""
    id: str
    email: str
    password_hash: str
    full_name: str
    role: str = "user"
    subscription_tier: str = "free"
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


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


class UserService:
    """Service for user management operations"""
    
    def __init__(self, db_session=None):
        """
        Initialize user service
        
        Args:
            db_session: Database session (optional, for testing)
        """
        self.db = db_session
    
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
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
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
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    def create_user(self, user_data: UserCreate) -> UserInDB:
        """
        Create a new user
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user object
        """
        now = datetime.utcnow()
        user = UserInDB(
            id=str(uuid.uuid4()),
            email=user_data.email,
            password_hash=self.hash_password(user_data.password),
            full_name=user_data.full_name,
            role="user",
            subscription_tier="free",
            created_at=now,
            updated_at=now,
            is_active=True
        )
        
        # TODO: Save to database
        # self.db.add(user)
        # self.db.commit()
        
        return user
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Get user by email address
        
        Args:
            email: User email
            
        Returns:
            User object or None if not found
        """
        # TODO: Query database
        # return self.db.query(User).filter(User.email == email).first()
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        # TODO: Query database
        # return self.db.query(User).filter(User.id == user_id).first()
        return None
    
    def authenticate_user(self, email: str, password: str) -> Optional[UserInDB]:
        """
        Authenticate a user with email and password
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.get_user_by_email(email)  # type: ignore[assignment]
        
        if not user:
            return None
        
        if not self.verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[UserInDB]:
        """
        Update user information
        
        Args:
            user_id: User ID
            user_data: Updated user data
            
        Returns:
            Updated user object or None if not found
        """
        user = self.get_user_by_id(user_id)  # type: ignore[assignment]
        
        if not user:
            return None
        
        # Update fields
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        if user_data.email is not None:
            user.email = user_data.email
        
        user.updated_at = datetime.utcnow()
        
        # TODO: Save to database
        # self.db.commit()
        
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user (soft delete by setting is_active=False)
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        user = self.get_user_by_id(user_id)  # type: ignore[assignment]
        
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        # TODO: Save to database
        # self.db.commit()
        
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
        user = self.get_user_by_id(user_id)  # type: ignore[assignment]
        
        if not user:
            return False
        
        user.password_hash = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # TODO: Save to database
        # self.db.commit()
        
        return True
    
    def to_response(self, user: UserInDB) -> UserResponse:
        """
        Convert UserInDB to UserResponse (remove sensitive data)
        
        Args:
            user: User object from database
            
        Returns:
            User response object without password
        """
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            subscription_tier=user.subscription_tier,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_active=user.is_active
        )

# Made with Bob
