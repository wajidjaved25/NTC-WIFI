"""
Shared Rate Limiter Instance

This module provides a singleton rate limiter instance that can be imported
throughout the application without causing circular import issues.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance that can be imported anywhere
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"]  # Default limit for all routes
)
