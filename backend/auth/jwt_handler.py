"""
JWT token handling for authentication
"""
import os
import redis
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

try:
    import jwt
    from jwt import InvalidTokenError, DecodeError, ExpiredSignatureError
except ImportError:
    raise ImportError(
        "PyJWT is required. Install it with: pip install PyJWT"
    )

logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Redis setup
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
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
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid and not revoked
    """
    if is_token_revoked(token):
        return False
        
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except InvalidTokenError:
        return False


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and return token payload
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        return None


def revoke_token(token: str) -> bool:
    """
    Revoke a token by adding to Redis blacklist
    """
    try:
        payload = decode_token(token)
        if not payload:
            return False
        
        # Calculate TTL until token expiry
        exp = payload.get("exp")
        if not exp:
            return False
            
        ttl = int(exp - datetime.now(timezone.utc).timestamp())
        if ttl > 0:
            redis_client.setex(f"revoked:{token}", ttl, "1")
        return True
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        return False


def is_token_revoked(token: str) -> bool:
    """
    Check if a token has been revoked
    """
    try:
        return redis_client.exists(f"revoked:{token}") > 0
    except Exception:
        return False


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """
    Generate a new access token from a valid refresh token
    """
    if is_token_revoked(refresh_token):
        return None
        
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        return None
    
    user_data = {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role")
    }
    
    return create_access_token(user_data)
