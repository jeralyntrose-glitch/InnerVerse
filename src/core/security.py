"""
Security Configuration
CSRF protection, rate limiting, and other security features
"""
import secrets
from collections import deque
from datetime import datetime, timedelta
from typing import Tuple
from fastapi import Request, HTTPException, status
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import BaseModel

from .config import get_settings
from .logging import setup_logging

logger = setup_logging(__name__)
settings = get_settings()


# CSRF Configuration
class CsrfSettings(BaseModel):
    """CSRF protection settings"""
    secret_key: str = settings.CSRF_SECRET_KEY or secrets.token_urlsafe(32)
    cookie_samesite: str = settings.COOKIE_SAMESITE
    cookie_secure: bool = settings.COOKIE_SECURE
    cookie_httponly: bool = True


@CsrfProtect.load_config
def get_csrf_config():
    """Load CSRF configuration"""
    return CsrfSettings()


# Rate Limiting
class RateLimiter:
    """
    Simple in-memory rate limiter
    For production, consider Redis-based rate limiting
    """
    
    def __init__(self, max_requests: int = 100, window_hours: int = 1):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in window
            window_hours: Time window in hours
        """
        self.max_requests = max_requests
        self.window_hours = window_hours
        self.requests = deque(maxlen=10000)  # Keep last 10k requests
        logger.info(f"Rate limiter initialized: {max_requests} req/{window_hours}h")
    
    def check_rate_limit(self, identifier: str = None) -> Tuple[bool, int]:
        """
        Check if rate limit is exceeded
        
        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            
        Returns:
            Tuple of (is_allowed, current_count)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, 0
        
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.window_hours)
        
        # Remove old requests
        while self.requests and self.requests[0][0] < cutoff_time:
            self.requests.popleft()
        
        # Count requests for this identifier (or all if no identifier)
        if identifier:
            request_count = sum(1 for ts, id in self.requests if id == identifier)
        else:
            request_count = len(self.requests)
        
        # Check limit
        if request_count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier or 'global'}: {request_count}")
            return False, request_count
        
        # Record this request
        self.requests.append((now, identifier))
        return True, request_count


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            max_requests=settings.RATE_LIMIT_PER_HOUR,
            window_hours=1
        )
    return _rate_limiter


async def check_rate_limit(request: Request) -> None:
    """
    FastAPI dependency for rate limiting
    
    Usage:
        @app.get("/api/endpoint", dependencies=[Depends(check_rate_limit)])
        async def endpoint():
            ...
    """
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    limiter = get_rate_limiter()
    client_ip = request.client.host if request.client else "unknown"
    
    is_allowed, count = limiter.check_rate_limit(client_ip)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Max {limiter.max_requests} requests per hour.",
                "retry_after": 3600  # seconds
            }
        )


def validate_api_key(api_key: str = None) -> bool:
    """
    Validate API key for protected endpoints
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid, False otherwise
    """
    # TODO: Implement proper API key validation
    # For now, just check if any key is provided
    return bool(api_key)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, considering proxies
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (from proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP if multiple
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    from pathlib import Path
    
    # Remove any path components
    filename = Path(filename).name
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename or "unnamed_file"

