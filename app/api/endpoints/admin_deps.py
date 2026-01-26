"""
Admin-specific dependencies.
"""
from fastapi import Depends, HTTPException, status

from app.api.endpoints.auth import get_current_user, User


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

