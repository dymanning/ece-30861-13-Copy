"""
Security module: JWT verification, RBAC, and rate limiting.
Designed to be non-intrusive and not break existing functionality.
"""
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import defaultdict
import time

from fastapi import HTTPException, status, Header
import jwt


# Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-not-for-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "ece-461-registry")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "ece-461-api")

# Simple in-memory rate limiting (maps IP:endpoint -> [timestamps])
# In production, use Redis or similar
_rate_limit_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT_WINDOW_SECS = 60
RATE_LIMIT_MAX_REQUESTS = 100  # Per endpoint per minute


def verify_jwt_token(
    authorization: Optional[str] = Header(None, alias="X-Authorization")
) -> Dict[str, Any]:
    """
    Verify JWT token from X-Authorization header.
    Checks signature, expiration, issuer, and audience.
    
    Args:
        authorization: JWT token from X-Authorization header
    
    Returns:
        Decoded token claims
    
    Raises:
        HTTPException 401 if token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Remove "Bearer " prefix if present
    token = authorization.replace("Bearer ", "").replace("bearer ", "")
    
    try:
        # Verify signature, expiration, issuer, audience
        # If JWT_SECRET is default (dev), still verify but don't reject
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"verify_signature": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(token: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dependency to enforce admin role.
    
    Args:
        token: Decoded JWT token from verify_jwt_token
    
    Returns:
        Token claims
    
    Raises:
        HTTPException 403 if user lacks admin role
    """
    role = token.get("role", "user")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return token


def require_role(required_role: str):
    """
    Factory function to create role-checking dependencies.
    
    Usage:
        @app.delete("/something")
        def delete_something(token: Dict = Depends(require_role("admin"))):
            ...
    
    Args:
        required_role: Role name to require (e.g., "admin", "editor")
    
    Returns:
        Dependency function
    """
    def check_role(token: Dict[str, Any]) -> Dict[str, Any]:
        role = token.get("role", "user")
        if role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return token
    return check_role


def validate_regex_safe(regex_pattern: str, max_length: int = 1000) -> bool:
    """
    Validate regex pattern for safety against ReDoS attacks.
    
    Checks:
    - Pattern length < max_length
    - Pattern compiles without error
    - Pattern doesn't use nested quantifiers (basic check)
    
    Args:
        regex_pattern: Regex string to validate
        max_length: Maximum allowed pattern length
    
    Returns:
        True if pattern is safe
    
    Raises:
        HTTPException 400 if pattern is invalid or unsafe
    """
    # Check length
    if len(regex_pattern) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Regex pattern exceeds {max_length} character limit"
        )
    
    # Try to compile
    try:
        re.compile(regex_pattern)
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {str(e)}"
        )
    
    # Check for obviously dangerous patterns (nested quantifiers)
    dangerous_patterns = [
        r'\([^)]*\*[^)]*\)+',  # (pattern*)+
        r'\([^)]*\+[^)]*\)+',  # (pattern+)+
        r'\([^)]*\{[^)]*\}[^)]*\)+',  # (pattern{n,m})+
    ]
    
    for dangerous in dangerous_patterns:
        if re.search(dangerous, regex_pattern):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Regex pattern contains nested quantifiers (ReDoS risk)"
            )
    
    return True


def validate_file_size(file_size_bytes: int, max_size_mb: int = 200) -> bool:
    """
    Validate file size.
    
    Args:
        file_size_bytes: Size of file in bytes
        max_size_mb: Maximum allowed size in MB
    
    Returns:
        True if file size is valid
    
    Raises:
        HTTPException 413 if file is too large
    """
    max_bytes = max_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {max_size_mb}MB limit"
        )
    return True


def check_rate_limit(key: str, limit: int = RATE_LIMIT_MAX_REQUESTS) -> bool:
    """
    Simple in-memory rate limiting.
    
    Args:
        key: Unique key for this rate limit bucket (e.g., "user_123:upload")
        limit: Maximum requests per RATE_LIMIT_WINDOW_SECS
    
    Returns:
        True if request is allowed
    
    Raises:
        HTTPException 429 if rate limit exceeded
    """
    now = time.time()
    timestamps = _rate_limit_store[key]
    
    # Remove old timestamps outside the window
    timestamps[:] = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW_SECS]
    
    # Check if we're over the limit
    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} requests per minute"
        )
    
    # Add current timestamp
    timestamps.append(now)
    return True


def create_jwt_token(
    user_id: str,
    role: str = "user",
    expires_in_hours: Optional[int] = None
) -> str:
    """
    Create a JWT token (for testing/development).
    
    Args:
        user_id: User identifier
        role: User role (default "user")
        expires_in_hours: Token expiration time (default from config)
    
    Returns:
        JWT token string
    """
    if expires_in_hours is None:
        expires_in_hours = JWT_EXPIRATION_HOURS
    
    now = datetime.utcnow()
    expiry = now + timedelta(hours=expires_in_hours)
    
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "iat": now,
        "exp": expiry,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Decode-only function (for testing/verification)
def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token without verification (for internal use/testing only).
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded claims
    """
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        options={"verify_signature": False}
    )
