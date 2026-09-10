"""Authentication dependencies for FastAPI."""
from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from salesagent.auth.jwt import verify_token

log = structlog.get_logger()

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials from request header

    Returns:
        User payload dict from JWT token

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token = credentials.credentials

    payload = verify_token(token)

    if payload is None:
        log.warning("Invalid or expired token", token_prefix=token[:20])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user info from payload
    username = payload.get("sub")
    if username is None:
        log.error("Token missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    log.info("User authenticated", username=username, role=payload.get("role"))

    return payload


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Dependency to get current active user (can be extended to check user status).

    Args:
        current_user: User payload from get_current_user

    Returns:
        User payload dict

    Raises:
        HTTPException: 403 if user is disabled
    """
    # Future: Check if user is disabled in database
    # if current_user.get("disabled"):
    #     raise HTTPException(status_code=403, detail="User account is disabled")

    return current_user
