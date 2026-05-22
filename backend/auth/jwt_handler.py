"""
JWT token handling for authentication
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

try:
    import jwt
    from jwt import InvalidTokenError, DecodeError, ExpiredSignatureError
except ImportError:
    raise ImportError(
        "PyJWT is required. Install it with: pip install PyJWT"
    )


# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration
    
    Args:
        data: Payload data to encode in the token
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid
    
    Args:
        token: JWT token string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except InvalidTokenError:
        return False


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and return token payload
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError:
        return None


def revoke_token(token: str) -> bool:
    """
    Revoke a token (add to blacklist)
    
    Note: This is a placeholder. In production, implement with Redis
    to store revoked tokens until their expiration.
    
    Args:
        token: JWT token string to revoke
        
    Returns:
        True if successfully revoked
    """
    # TODO: Implement with Redis blacklist
    # redis_client.setex(f"revoked:{token}", ttl, "1")
    return True


def is_token_revoked(token: str) -> bool:
    """
    Check if a token has been revoked
    
    Args:
        token: JWT token string
        
    Returns:
        True if revoked, False otherwise
    """
    # TODO: Implement with Redis blacklist check
    # return redis_client.exists(f"revoked:{token}")
    return False


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    Generate a new access token from a valid refresh token
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New access token or None if refresh token is invalid
    """
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        return None
    
    # Create new access token with user data
    user_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role")
    }
    
    return create_access_token(user_data)

# Made with Bob
