"""
Admin API - Courses
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_schemas import UserSchema as User
from api.deps import get_current_user
from core.database import get_db_session
from models.config_models import Course

router = APIRouter()

# 权限依赖
async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username != "admin": # MVP check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

# Models
class CourseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    difficulty_level: str = "beginner"
    is_active: bool = True

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty_level: Optional[str] = None
    is_active: Optional[bool] = None

class CourseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    difficulty_level: str
    is_active: bool
    
    class Config:
        from_attributes = True

# Routes
@router.post("", response_model=CourseResponse)
async def create_course(
    course: CourseCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """创建新课程"""
    db_course = Course(
        id=str(uuid.uuid4()),
        name=course.name,
        description=course.description,
        difficulty_level=course.difficulty_level,
        is_active=course.is_active
    )
    db.add(db_course)
    await db.commit()
    await db.refresh(db_course)
    return db_course

@router.get("", response_model=List[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """列出所有课程"""
    result = await db.execute(select(Course))
    return result.scalars().all()

@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """获取课程详情"""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_update: CourseUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """更新课程"""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_data = course_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(course, key, value)
    
    await db.commit()
    await db.refresh(course)
    return course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """删除课程"""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    await db.delete(course)
    await db.commit()
    return None
