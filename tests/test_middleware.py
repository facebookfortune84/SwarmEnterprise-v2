"""
Unit tests for authentication middleware
"""
import pytest
from fastapi import HTTPException
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db.base import Base
from backend.db.models import User
from backend.auth.middleware import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_current_superadmin_user,
)
from backend.auth.jwt_handler import create_access_token


class TestAuthMiddleware:
    """Test suite for authentication middleware"""

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
    def active_user(self, db_session):
        """Create an active user in database"""
        user = User(
            id="user123",
            email="test@example.com",
            password_hash="hashed",
            full_name="Test User",
            role="user",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def inactive_user(self, db_session):
        """Create an inactive user in database"""
        user = User(
            id="inactive123",
            email="inactive@example.com",
            password_hash="hashed",
            full_name="Inactive User",
            role="user",
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token"""
        token_data = {"sub": "user123", "email": "test@example.com", "role": "user"}
        token = create_access_token(token_data)

        # Mock credentials
        credentials = Mock()
        credentials.credentials = token

        user = await get_current_user(credentials)

        assert user is not None
        assert user["id"] == "user123"
        assert user["email"] == "test@example.com"
        assert user["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token"""
        credentials = Mock()
        credentials.credentials = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_revoked_token(self):
        """Test getting current user with revoked token"""
        from backend.auth.jwt_handler import revoke_token

        token_data = {"sub": "user123"}
        token = create_access_token(token_data)

        # Revoke the token
        revoke_token(token)

        credentials = Mock()
        credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, active_user):
        """Test getting active user succeeds"""
        current_user = {"id": active_user.id, "email": active_user.email, "role": active_user.role}

        with patch("backend.auth.middleware.SessionLocal", return_value=self.SessionLocal()):
            result = await get_current_active_user(current_user)

        assert result == current_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, inactive_user):
        """Test getting inactive user fails"""
        current_user = {
            "id": inactive_user.id,
            "email": inactive_user.email,
            "role": inactive_user.role,
        }

        with patch("backend.auth.middleware.SessionLocal", return_value=self.SessionLocal()):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_active_user(current_user)

        assert exc_info.value.status_code == 403
        assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_active_user_not_found(self):
        """Test getting non-existent user fails"""
        current_user = {"id": "nonexistent", "email": "none@example.com", "role": "user"}

        with patch("backend.auth.middleware.SessionLocal", return_value=self.SessionLocal()):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_active_user(current_user)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_current_admin_user_success(self):
        """Test admin user access succeeds"""
        current_user = {"id": "admin123", "email": "admin@example.com", "role": "admin"}

        result = await get_current_admin_user(current_user)

        assert result == current_user

    @pytest.mark.asyncio
    async def test_get_current_admin_user_superadmin_success(self):
        """Test superadmin can access admin endpoints"""
        current_user = {"id": "super123", "email": "super@example.com", "role": "superadmin"}

        result = await get_current_admin_user(current_user)

        assert result == current_user

    @pytest.mark.asyncio
    async def test_get_current_admin_user_regular_user_fails(self):
        """Test regular user cannot access admin endpoints"""
        current_user = {"id": "user123", "email": "user@example.com", "role": "user"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_superadmin_user_success(self):
        """Test superadmin user access succeeds"""
        current_user = {"id": "super123", "email": "super@example.com", "role": "superadmin"}

        result = await get_current_superadmin_user(current_user)

        assert result == current_user

    @pytest.mark.asyncio
    async def test_get_current_superadmin_user_admin_fails(self):
        """Test admin cannot access superadmin endpoints"""
        current_user = {"id": "admin123", "email": "admin@example.com", "role": "admin"}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_superadmin_user(current_user)

        assert exc_info.value.status_code == 403
        assert "superadmin" in exc_info.value.detail.lower()


# Made with Bob
