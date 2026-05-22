"""
Unit tests for JWT token handling
"""
from datetime import timedelta
from backend.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    refresh_access_token,
)


class TestJWTHandler:
    """Test suite for JWT token operations"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "user"
        }
        
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_access_token_with_custom_expiry(self):
        """Test access token with custom expiration"""
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=30)
        
        token = create_access_token(data, expires_delta=expires_delta)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "user"
        }
        
        token = create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Test verification of valid token"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        assert verify_token(token) is True
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        invalid_token = "invalid.token.here"
        
        assert verify_token(invalid_token) is False
    
    def test_verify_expired_token(self):
        """Test verification of expired token"""
        data = {"sub": "user123"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)
        
        assert verify_token(token) is False
    
    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "admin"
        }
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        
        payload = decode_token(invalid_token)
        
        assert payload is None
    
    def test_refresh_access_token_success(self):
        """Test refreshing access token with valid refresh token"""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "user"
        }
        refresh_token = create_refresh_token(data)
        
        new_access_token = refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        payload = decode_token(new_access_token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"
    
    def test_refresh_access_token_with_access_token_fails(self):
        """Test that using access token for refresh fails"""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        
        new_token = refresh_access_token(access_token)
        
        assert new_token is None
    
    def test_refresh_access_token_with_invalid_token(self):
        """Test refresh with invalid token"""
        invalid_token = "invalid.token.here"
        
        new_token = refresh_access_token(invalid_token)
        
        assert new_token is None
    
    def test_token_contains_required_fields(self):
        """Test that tokens contain all required fields"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload is not None
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
    
    def test_refresh_token_type(self):
        """Test that refresh token has correct type"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["type"] == "refresh"
    
    def test_access_token_type(self):
        """Test that access token has correct type"""
        data = {"sub": "user123"}
        token = create_access_token(data)
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["type"] == "access"


# Made with Bob