"""
Admin-specific dependencies.
"""
from fastapi import Depends, HTTPException, status

from api.auth_schemas import UserSchema as User
from api.deps import get_current_user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

