"""
Authentication and authorization middleware
"""
from typing import Optional, Callable
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import decode_token, is_token_revoked


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User data from token
        
    Raises:
        HTTPException: If token is invalid or revoked
    """
    token = credentials.credentials
    
    # Check if token is revoked
    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode token
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current active user (can be extended to check user status in DB)
    
    Args:
        current_user: Current user from token
        
    Returns:
        Active user data
        
    Raises:
        HTTPException: If user is inactive
    """
    # TODO: Check if user is active in database
    # user = db.query(User).filter(User.id == current_user["id"]).first()
    # if not user or not user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


async def get_current_admin_user(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Get current user and verify admin role
    
    Args:
        current_user: Current active user
        
    Returns:
        Admin user data
        
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


async def get_current_superadmin_user(
    current_user: dict = Depends(get_current_active_user)
) -> dict:
    """
    Get current user and verify superadmin role
    
    Args:
        current_user: Current active user
        
    Returns:
        Superadmin user data
        
    Raises:
        HTTPException: If user is not a superadmin
    """
    if current_user.get("role") != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    
    return current_user


class RateLimitMiddleware:
    """
    Rate limiting middleware
    
    Note: This is a basic implementation. For production, use Redis-based
    rate limiting with libraries like slowapi or fastapi-limiter.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Maximum requests per minute per IP
        """
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # IP -> (count, timestamp)
    
    async def __call__(self, request: Request, call_next: Callable):
        """
        Process request with rate limiting
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        import time
        
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        self.request_counts = {
            ip: (count, timestamp)
            for ip, (count, timestamp) in self.request_counts.items()
            if current_time - timestamp < 60
        }
        
        # Check rate limit
        if client_ip in self.request_counts:
            count, timestamp = self.request_counts[client_ip]
            if current_time - timestamp < 60:
                if count >= self.requests_per_minute:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded. Please try again later."
                    )
                self.request_counts[client_ip] = (count + 1, timestamp)
            else:
                self.request_counts[client_ip] = (1, current_time)
        else:
            self.request_counts[client_ip] = (1, current_time)
        
        response = await call_next(request)
        return response


def verify_api_key(api_key: str) -> bool:
    """
    Verify API key for programmatic access
    
    Args:
        api_key: API key to verify
        
    Returns:
        True if valid, False otherwise
    """
    # TODO: Implement API key verification with database
    # api_key_record = db.query(APIKey).filter(APIKey.key == api_key).first()
    # return api_key_record is not None and api_key_record.is_active
    return False


async def get_api_key(
    request: Request
) -> Optional[str]:
    """
    Extract API key from request headers
    
    Args:
        request: FastAPI request
        
    Returns:
        API key or None
    """
    api_key = request.headers.get("X-API-Key")
    return api_key


async def verify_api_key_auth(
    api_key: Optional[str] = Depends(get_api_key)
) -> dict:
    """
    Verify API key authentication
    
    Args:
        api_key: API key from headers
        
    Returns:
        API key owner data
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key or not verify_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    # TODO: Get API key owner from database
    # api_key_record = db.query(APIKey).filter(APIKey.key == api_key).first()
    # return {"user_id": api_key_record.user_id, "scope": api_key_record.scope}
    
    return {"user_id": "api_user", "scope": "read:write"}

# Made with Bob
