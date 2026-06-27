"""
Unit tests for User Service
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.auth.user_service import (
    UserService,
    UserCreate,
    UserUpdate,
    UserResponse,
)


class TestUserService:
    """Test suite for UserService"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Set up in-memory database for testing"""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        yield
        Base.metadata.drop_all(self.engine)

    @pytest.fixture
    def db_session(self):
        """Get a database session"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def user_service(self, db_session):
        """Create a UserService instance for testing"""
        return UserService(db=db_session)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user creation data"""
        return UserCreate(
            email="test@example.com", password="SecurePass123!", full_name="Test User"
        )

    def test_hash_password(self, user_service):
        """Test password hashing"""
        password = "MySecurePassword123"
        hashed = user_service.hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_different_hashes(self, user_service):
        """Test that same password produces different hashes (due to salt)"""
        password = "MySecurePassword123"
        hash1 = user_service.hash_password(password)
        hash2 = user_service.hash_password(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2

    def test_verify_password_correct(self, user_service):
        """Test password verification with correct password"""
        password = "MySecurePassword123"
        hashed = user_service.hash_password(password)

        assert user_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, user_service):
        """Test password verification with incorrect password"""
        password = "MySecurePassword123"
        wrong_password = "WrongPassword456"
        hashed = user_service.hash_password(password)

        assert user_service.verify_password(wrong_password, hashed) is False

    def test_create_user(self, user_service, sample_user_data):
        """Test user creation"""
        user = user_service.create_user(sample_user_data)

        assert user is not None
        assert user.email == sample_user_data.email
        assert user.full_name == sample_user_data.full_name
        assert user.password_hash != sample_user_data.password
        assert user.role == "user"
        assert user.subscription_tier == "free"
        assert user.is_active is True
        assert user.id is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_create_user_password_hashed(self, user_service, sample_user_data):
        """Test that password is hashed during user creation"""
        user = user_service.create_user(sample_user_data)

        # Password should be hashed
        assert user.password_hash != sample_user_data.password
        # But should verify correctly
        assert user_service.verify_password(sample_user_data.password, user.password_hash) is True

    def test_user_create_validation_short_password(self):
        """Test that short passwords are rejected"""
        with pytest.raises(ValueError, match="at least 8 characters"):
            UserCreate(email="test@example.com", password="short", full_name="Test User")

    def test_user_create_validation_invalid_email(self):
        """Test that invalid emails are rejected"""
        with pytest.raises(ValueError):
            UserCreate(email="not-an-email", password="SecurePass123!", full_name="Test User")

    def test_to_response_removes_password(self, user_service, sample_user_data):
        """Test that UserResponse doesn't include password"""
        user = user_service.create_user(sample_user_data)
        response = user_service.to_response(user)

        assert isinstance(response, UserResponse)
        assert response.id == user.id
        assert response.email == user.email
        assert response.full_name == user.full_name
        assert response.role == user.role
        assert not hasattr(response, "password_hash")
        assert not hasattr(response, "password")

    def test_reset_password(self, user_service, sample_user_data):
        """Test password reset functionality"""
        # Create a real user
        user = user_service.create_user(sample_user_data)
        user_id = user.id

        new_password = "NewPassword456"
        result = user_service.reset_password(user_id, new_password)

        assert result is True
        # Need to refresh to get updated password_hash from DB if not already updated
        assert user_service.verify_password(new_password, user.password_hash) is True
        assert user_service.verify_password(sample_user_data.password, user.password_hash) is False

    def test_reset_password_user_not_found(self, user_service):
        """Test password reset with non-existent user"""
        result = user_service.reset_password("nonexistent", "NewPassword123")

        assert result is False

    def test_user_update(self, user_service, sample_user_data):
        """Test user update functionality"""
        # Create a real user
        user = user_service.create_user(sample_user_data)
        user_id = user.id

        update_data = UserUpdate(full_name="New Name", email="new@example.com")

        updated_user = user_service.update_user(user_id, update_data)

        assert updated_user is not None
        assert updated_user.full_name == "New Name"
        assert updated_user.email == "new@example.com"

    def test_user_update_partial(self, user_service, sample_user_data):
        """Test partial user update"""
        # Create a real user
        user = user_service.create_user(sample_user_data)
        user_id = user.id

        # Only update full_name
        update_data = UserUpdate(full_name="New Name")
        updated_user = user_service.update_user(user_id, update_data)

        assert updated_user is not None
        assert updated_user.full_name == "New Name"
        assert updated_user.email == sample_user_data.email  # Unchanged

    def test_delete_user(self, user_service, sample_user_data):
        """Test user deletion (soft delete)"""
        # Create a real user
        user = user_service.create_user(sample_user_data)
        user_id = user.id

        result = user_service.delete_user(user_id)

        assert result is True
        assert user.is_active is False

    def test_delete_user_not_found(self, user_service):
        """Test deleting non-existent user"""
        result = user_service.delete_user("nonexistent")

        assert result is False

    def test_authenticate_user_success(self, user_service, sample_user_data):
        """Test successful user authentication"""
        # Create a real user
        user_service.create_user(sample_user_data)

        authenticated_user = user_service.authenticate_user(
            sample_user_data.email, sample_user_data.password
        )

        assert authenticated_user is not None
        assert authenticated_user.email == sample_user_data.email

    def test_authenticate_user_wrong_password(self, user_service, sample_user_data):
        """Test authentication with wrong password"""
        # Create a real user
        user_service.create_user(sample_user_data)

        authenticated_user = user_service.authenticate_user(sample_user_data.email, "WrongPassword")

        assert authenticated_user is None

    def test_authenticate_user_not_found(self, user_service):
        """Test authentication with non-existent user"""
        authenticated_user = user_service.authenticate_user("nonexistent@example.com", "password")

        assert authenticated_user is None

    def test_authenticate_inactive_user(self, user_service, sample_user_data):
        """Test that inactive users cannot authenticate"""
        # Create a real user
        user = user_service.create_user(sample_user_data)
        user.is_active = False
        user_service.db.commit()

        authenticated_user = user_service.authenticate_user(
            sample_user_data.email, sample_user_data.password
        )

        assert authenticated_user is None


# Made with Bob
