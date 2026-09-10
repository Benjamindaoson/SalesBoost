"""Rate limiting configuration and utilities."""
from __future__ import annotations

import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

log = structlog.get_logger()


def get_user_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting.

    Uses authenticated user ID if available, otherwise falls back to IP address.

    Args:
        request: FastAPI request object

    Returns:
        User identifier string
    """
    # Try to get authenticated user from request state
    if hasattr(request.state, "user"):
        user = request.state.user
        if user and isinstance(user, dict):
            user_id = user.get("user_id") or user.get("sub")
            if user_id:
                log.debug("Rate limit by user", user_id=user_id)
                return f"user:{user_id}"

    # Fall back to IP address
    ip = get_remote_address(request)
    log.debug("Rate limit by IP", ip=ip)
    return f"ip:{ip}"


# Create limiter instance with global limits
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["100/minute", "1000/hour", "5000/day"],
    storage_uri="memory://",  # In-memory storage (use Redis in production)
)
