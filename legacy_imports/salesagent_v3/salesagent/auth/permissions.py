"""Authorization and permission checking utilities."""
from __future__ import annotations

from enum import Enum
from typing import Callable

import structlog
from fastapi import Depends, HTTPException, status

from salesagent.auth.dependencies import get_current_user

log = structlog.get_logger()


class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


def require_role(*allowed_roles: str) -> Callable:
    """
    Dependency to check if user has required role.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            current_user: dict = Depends(require_role("admin"))
        ):
            ...

    Args:
        allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Dependency function that validates user role

    Raises:
        HTTPException: 403 if user doesn't have required role
    """
    async def check_role(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "user")

        if user_role not in allowed_roles:
            log.warning(
                "Access denied - insufficient role",
                user=current_user.get("sub"),
                user_role=user_role,
                required_roles=allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )

        log.info(
            "Role check passed",
            user=current_user.get("sub"),
            role=user_role,
        )
        return current_user

    return check_role


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to require admin role.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(
            current_user: dict = Depends(require_admin)
        ):
            ...

    Args:
        current_user: Current authenticated user

    Returns:
        User dict if admin

    Raises:
        HTTPException: 403 if user is not admin
    """
    user_role = current_user.get("role", "user")

    if user_role != Role.ADMIN:
        log.warning(
            "Access denied - admin required",
            user=current_user.get("sub"),
            user_role=user_role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


def check_resource_ownership(
    resource_user_id: str | None,
    current_user: dict,
    allow_admin: bool = True,
) -> None:
    """
    Check if user owns the resource or is admin.

    Args:
        resource_user_id: User ID that owns the resource
        current_user: Current authenticated user
        allow_admin: Whether admin can access regardless of ownership

    Raises:
        HTTPException: 403 if user doesn't own resource and isn't admin
    """
    user_role = current_user.get("role", "user")
    user_id = current_user.get("user_id") or current_user.get("sub")

    # Admin can access everything
    if allow_admin and user_role == Role.ADMIN:
        return

    # Check ownership
    if resource_user_id != user_id:
        log.warning(
            "Access denied - not resource owner",
            user=current_user.get("sub"),
            resource_owner=resource_user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own resources.",
        )


def require_ownership_or_admin(
    resource_user_id: str | None,
) -> Callable:
    """
    Dependency factory to check resource ownership or admin role.

    Usage:
        @router.get("/sessions/{session_id}")
        async def get_session(
            session_id: str,
            db: AsyncSession = Depends(get_db),
            current_user: dict = Depends(get_current_user),
        ):
            session = await db.get(SessionModel, session_id)
            check_resource_ownership(session.user_id, current_user)
            return session

    Args:
        resource_user_id: User ID that owns the resource

    Returns:
        Dependency function
    """
    async def check(current_user: dict = Depends(get_current_user)) -> dict:
        check_resource_ownership(resource_user_id, current_user)
        return current_user

    return check
