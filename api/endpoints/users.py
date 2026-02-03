"""
User Management API

Provides CRUD operations for users and user statistics.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from api.deps import require_user, require_admin, audit_access
from api.auth_schemas import UserSchema as CurrentUser
from api.auth_utils import hash_password
from app.models.user import User, UserRole
from app.models.session import Session
from app.models.evaluation import Evaluation

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Schemas ====================

class UserCreate(BaseModel):
    """Schema for creating a user"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.STUDENT
    full_name: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[UserRole] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    role: str
    full_name: Optional[str]
    is_active: bool
    avatar_url: Optional[str]
    phone: Optional[str]
    organization: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list"""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class UserStatistics(BaseModel):
    """User training statistics"""
    total_sessions: int
    completed_sessions: int
    average_score: float
    total_training_hours: float
    courses_enrolled: int


# ==================== Helper Functions ====================

def _serialize_user(user: User) -> UserResponse:
    """Convert User model to UserResponse"""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        full_name=user.full_name,
        is_active=user.is_active,
        avatar_url=user.avatar_url,
        phone=user.phone,
        organization=user.organization,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat()
    )


def _check_user_access(current_user: CurrentUser, target_user_id: int) -> None:
    """Check if current user can access target user's data"""
    if current_user.role != "admin" and current_user.id != target_user_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this user's data"
        )


# ==================== API Endpoints ====================

@router.post("", response_model=UserResponse, dependencies=[Depends(audit_access)])
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Create a new user (Admin only)

    Requires admin role.
    """
    logger.info(f"Creating user: {user_data.username} by admin {current_user.id}")

    # Check if username already exists
    username_query = select(User).where(User.username == user_data.username)
    username_result = await db.execute(username_query)
    if username_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Check if email already exists
    email_query = select(User).where(User.email == user_data.email)
    email_result = await db.execute(email_query)
    if email_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        full_name=user_data.full_name,
        phone=user_data.phone,
        organization=user_data.organization,
        is_active=True
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User created successfully: {user.id}")
    return _serialize_user(user)


@router.get("", response_model=UserListResponse, dependencies=[Depends(audit_access)])
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in username and email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    List users with filtering and pagination (Admin only)

    Available filters:
    - role: admin, teacher, student
    - is_active: true/false
    - search: search in username and email
    """
    logger.info(f"Listing users for admin {current_user.id}")

    # Build query
    query = select(User)

    # Apply filters
    if role:
        try:
            role_enum = UserRole(role)
            query = query.where(User.role == role_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    logger.info(f"Found {total} users, returning page {page}")

    return UserListResponse(
        items=[_serialize_user(u) for u in users],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(audit_access)])
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_user)
):
    """
    Get user details by ID

    Users can only access their own data unless they are admin.
    """
    logger.info(f"Getting user {user_id} for user {current_user.id}")

    # Check access permission
    _check_user_access(current_user, user_id)

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return _serialize_user(user)


@router.put("/{user_id}", response_model=UserResponse, dependencies=[Depends(audit_access)])
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_user)
):
    """
    Update user

    Users can only update their own data unless they are admin.
    Only admins can change roles.
    """
    logger.info(f"Updating user {user_id} by user {current_user.id}")

    # Check access permission
    _check_user_access(current_user, user_id)

    # Get existing user
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)

    # Only admins can change roles
    if 'role' in update_data and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change user roles")

    # Check username uniqueness if changing
    if 'username' in update_data and update_data['username'] != user.username:
        username_query = select(User).where(User.username == update_data['username'])
        username_result = await db.execute(username_query)
        if username_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already exists")

    # Check email uniqueness if changing
    if 'email' in update_data and update_data['email'] != user.email:
        email_query = select(User).where(User.email == update_data['email'])
        email_result = await db.execute(email_query)
        if email_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already exists")

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user_id} updated successfully")
    return _serialize_user(user)


@router.delete("/{user_id}", dependencies=[Depends(audit_access)])
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Delete user (Admin only)

    Requires admin role. This will also delete all associated sessions and evaluations.
    """
    logger.info(f"Deleting user {user_id} by admin {current_user.id}")

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Get existing user
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    await db.delete(user)
    await db.commit()

    logger.info(f"User {user_id} deleted successfully")
    return {"status": "success", "message": f"User {user_id} deleted"}


@router.patch("/{user_id}/activate", response_model=UserResponse, dependencies=[Depends(audit_access)])
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Activate user (Admin only)

    Requires admin role.
    """
    logger.info(f"Activating user {user_id} by admin {current_user.id}")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user_id} activated successfully")
    return _serialize_user(user)


@router.patch("/{user_id}/deactivate", response_model=UserResponse, dependencies=[Depends(audit_access)])
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_admin)
):
    """
    Deactivate user (Admin only)

    Requires admin role.
    """
    logger.info(f"Deactivating user {user_id} by admin {current_user.id}")

    # Prevent self-deactivation
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user_id} deactivated successfully")
    return _serialize_user(user)


@router.get("/{user_id}/statistics", response_model=UserStatistics, dependencies=[Depends(audit_access)])
async def get_user_statistics(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(require_user)
):
    """
    Get user training statistics

    Users can only access their own statistics unless they are admin.
    """
    logger.info(f"Getting statistics for user {user_id}")

    # Check access permission
    _check_user_access(current_user, user_id)

    # Verify user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # Get session statistics
    session_query = select(Session).where(Session.user_id == user_id)
    session_result = await db.execute(session_query)
    sessions = session_result.scalars().all()

    total_sessions = len(sessions)
    completed_sessions = len([s for s in sessions if s.status == "completed"])

    # Calculate average score
    scores = [s.final_score for s in sessions if s.final_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0.0

    # Calculate total training hours (from session durations)
    total_minutes = sum([
        (s.ended_at - s.started_at).total_seconds() / 60
        for s in sessions
        if s.ended_at and s.started_at
    ])
    total_training_hours = total_minutes / 60

    # Count unique courses enrolled
    unique_courses = len(set([s.course_id for s in sessions if s.course_id]))

    return UserStatistics(
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        average_score=round(average_score, 2),
        total_training_hours=round(total_training_hours, 2),
        courses_enrolled=unique_courses
    )
