"""
Simplified Courses API
"""
import logging
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...models.course import Course as CourseModel, CourseStatus

logger = logging.getLogger(__name__)
router = APIRouter()


class CourseResponse(BaseModel):
    id: int
    title: str
    description: str | None
    difficulty: int
    duration_minutes: int
    status: str
    category: str | None
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db_session)):
    """获取课程分类列表（从已发布课程中提取）"""
    query = select(CourseModel.category).where(
        CourseModel.status == CourseStatus.PUBLISHED,
        CourseModel.category.isnot(None),
        CourseModel.category != "",
    ).distinct()
    result = await db.execute(query)
    rows = result.scalars().all()
    categories = [r[0] for r in rows if r[0]]
    default = ["全部课程", "新客户开卡场景训练", "异议处理训练", "权益推荐场景", "合规话术训练", "白金卡销售话术"]
    merged = ["全部课程"] + [c for c in default[1:] if c not in categories] + [c for c in categories if c not in default]
    return list(dict.fromkeys(merged))


@router.get("", response_model=List[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取所有课程
    """
    logger.info("Fetching all courses")

    query = select(CourseModel).where(CourseModel.status == CourseStatus.PUBLISHED)
    result = await db.execute(query)
    courses = result.scalars().all()

    logger.info(f"Found {len(courses)} courses")

    return [
        CourseResponse(
            id=c.id,
            title=c.title,
            description=c.description,
            difficulty=c.difficulty,
            duration_minutes=c.duration_minutes or 0,
            status=c.status.value if hasattr(c.status, 'value') else str(c.status),
            category=c.category,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in courses
    ]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取特定课程
    """
    logger.info(f"Fetching course {course_id}")

    query = select(CourseModel).where(CourseModel.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()

    if not course:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Course not found")

    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        difficulty=course.difficulty,
        duration_minutes=course.duration_minutes or 0,
        status=course.status.value if hasattr(course.status, 'value') else str(course.status),
        category=course.category,
        updated_at=course.updated_at.isoformat() if course.updated_at else None,
    )
