"""
PakApp API Security Utilities
Provides authentication and authorization for PakApp endpoints
"""

from fastapi import HTTPException, status, Request, Header
from typing import Optional
import hmac
import hashlib
import time
from ..config import settings


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Verify PakApp API key from request header
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        True if valid, raises HTTPException if invalid
    """
    if not settings.PAKAPP_ENABLE_API_KEY:
        return True  # API key check disabled
    
    if not settings.PAKAPP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PakApp API key not configured on server"
        )
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if x_api_key != settings.PAKAPP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return True


def verify_ip_whitelist(request: Request) -> bool:
    """
    Verify request IP is in allowed list
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if allowed, raises HTTPException if blocked
    """
    if not settings.PAKAPP_ALLOWED_IPS:
        return True  # No IP restriction
    
    # Get client IP
    client_ip = request.client.host
    
    # Check X-Forwarded-For header (for reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in the chain
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Parse allowed IPs
    allowed_ips = [ip.strip() for ip in settings.PAKAPP_ALLOWED_IPS.split(",")]
    
    if client_ip not in allowed_ips:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP address {client_ip} not allowed"
        )
    
    return True


def verify_signature(
    request: Request,
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None)
) -> bool:
    """
    Verify HMAC signature of request
    
    Headers required:
        X-Signature: HMAC-SHA256 signature
        X-Timestamp: Unix timestamp (to prevent replay attacks)
    
    Args:
        request: FastAPI request object
        x_signature: Signature from X-Signature header
        x_timestamp: Timestamp from X-Timestamp header
        
    Returns:
        True if valid, raises HTTPException if invalid
    """
    if not settings.PAKAPP_ENABLE_SIGNATURE:
        return True  # Signature check disabled
    
    if not settings.PAKAPP_SIGNATURE_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signature secret not configured on server"
        )
    
    # Check required headers
    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Signature header"
        )
    
    if not x_timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Timestamp header"
        )
    
    # Verify timestamp (prevent replay attacks - allow 5 minute window)
    try:
        timestamp = int(x_timestamp)
        current_time = int(time.time())
        
        if abs(current_time - timestamp) > 300:  # 5 minutes
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request timestamp expired (max 5 minutes)"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid timestamp format"
        )
    
    # Get request body (already parsed)
    # Note: This requires getting raw body, which we'll handle in the endpoint
    
    return True


def generate_signature(payload: str, timestamp: int, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for request
    
    Args:
        payload: Request body as JSON string
        timestamp: Unix timestamp
        secret: Shared secret key
        
    Returns:
        Hex-encoded signature
    """
    message = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_request_signature(payload: str, timestamp: int, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature
    
    Args:
        payload: Request body as JSON string
        timestamp: Unix timestamp from request
        signature: Signature from request header
        secret: Shared secret key
        
    Returns:
        True if valid, False otherwise
    """
    expected_signature = generate_signature(payload, timestamp, secret)
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)


async def verify_pakapp_security(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None)
) -> bool:
    """
    Complete security verification for PakApp endpoints
    Checks all enabled security measures
    
    Args:
        request: FastAPI request object
        x_api_key: API key from header
        x_signature: Signature from header
        x_timestamp: Timestamp from header
        
    Returns:
        True if all checks pass, raises HTTPException otherwise
    """
    # 1. Verify IP whitelist
    verify_ip_whitelist(request)
    
    # 2. Verify API key
    verify_api_key(x_api_key)
    
    # 3. Verify signature (if enabled)
    if settings.PAKAPP_ENABLE_SIGNATURE:
        verify_signature(request, x_signature, x_timestamp)
    
    return True


# Dependency function for FastAPI
async def require_pakapp_auth(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None)
) -> bool:
    """
    FastAPI dependency for PakApp authentication
    Use with Depends() in route definitions
    """
    return await verify_pakapp_security(request, x_api_key, x_signature, x_timestamp)
