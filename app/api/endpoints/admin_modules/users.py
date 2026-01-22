"""
Admin API - Users
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db_session
from app.api.endpoints.auth import get_current_user, User
from app.models.saas_models import User as DBUser

router = APIRouter()


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    is_active: bool


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(DBUser).order_by(DBUser.created_at.desc()))
    return result.scalars().all()


@router.put("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(DBUser).where(DBUser.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = payload.is_active
    await db.commit()
    await db.refresh(db_user)
    return db_user
