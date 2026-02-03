"""
Course Management API

Provides CRUD operations for courses.
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from api.deps import require_user, require_admin, audit_access
from api.auth_schemas import UserSchema as User
from app.models.course import Course, CourseStatus
from app.models.task import Task

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Schemas ====================

class CourseCreate(BaseModel):
    """Schema for creating a course"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.DRAFT
    category: Optional[str] = None
    difficulty: int = Field(default=1, ge=1, le=5)
    duration_minutes: Optional[int] = None
    thumbnail_url: Optional[str] = None
    instructor_name: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CourseUpdate(BaseModel):
    """Schema for updating a course"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[CourseStatus] = None
    category: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    duration_minutes: Optional[int] = None
    thumbnail_url: Optional[str] = None
    instructor_name: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class CourseResponse(BaseModel):
    """Schema for course response"""
    id: int
    title: str
    description: Optional[str]
    status: str
    category: Optional[str]
    difficulty: int
    duration_minutes: Optional[int]
    thumbnail_url: Optional[str]
    instructor_name: Optional[str]
    learning_objectives: Optional[List[str]]
    prerequisites: Optional[List[str]]
    tags: Optional[List[str]]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    """Schema for paginated course list"""
    items: List[CourseResponse]
    total: int
    page: int
    page_size: int


class TaskSummary(BaseModel):
    """Summary of a task"""
    id: int
    title: str
    task_type: str
    status: str
    order: int
    points: int


# ==================== Helper Functions ====================

def _serialize_course(course: Course) -> CourseResponse:
    """Convert Course model to CourseResponse"""
    return CourseResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        status=course.status.value,
        category=course.category,
        difficulty=course.difficulty,
        duration_minutes=course.duration_minutes,
        thumbnail_url=course.thumbnail_url,
        instructor_name=course.instructor_name,
        learning_objectives=json.loads(course.learning_objectives or "[]"),
        prerequisites=json.loads(course.prerequisites or "[]"),
        tags=json.loads(course.tags or "[]"),
        created_at=course.created_at.isoformat(),
        updated_at=course.updated_at.isoformat()
    )


# ==================== API Endpoints ====================

@router.post("", response_model=CourseResponse, dependencies=[Depends(audit_access)])
async def create_course(
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Create a new course (Admin only)

    Requires admin role.
    """
    logger.info(f"Creating course: {course_data.title} by user {current_user.id}")

    # Create course instance
    course = Course(
        title=course_data.title,
        description=course_data.description,
        status=course_data.status,
        category=course_data.category,
        difficulty=course_data.difficulty,
        duration_minutes=course_data.duration_minutes,
        thumbnail_url=course_data.thumbnail_url,
        instructor_name=course_data.instructor_name,
        learning_objectives=json.dumps(course_data.learning_objectives or []),
        prerequisites=json.dumps(course_data.prerequisites or []),
        tags=json.dumps(course_data.tags or [])
    )

    db.add(course)
    await db.commit()
    await db.refresh(course)

    logger.info(f"Course created successfully: {course.id}")
    return _serialize_course(course)


@router.get("", response_model=CourseListResponse, dependencies=[Depends(audit_access)])
async def list_courses(
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[int] = Query(None, ge=1, le=5, description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    List courses with filtering and pagination

    Available filters:
    - status: draft, published, archived
    - category: course category
    - difficulty: 1-5
    - search: search in title and description
    """
    logger.info(f"Listing courses for user {current_user.id}")

    # Build query
    query = select(Course)

    # Apply filters
    if status:
        try:
            status_enum = CourseStatus(status)
            query = query.where(Course.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if category:
        query = query.where(Course.category == category)

    if difficulty:
        query = query.where(Course.difficulty == difficulty)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Course.title.ilike(search_pattern),
                Course.description.ilike(search_pattern)
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Course.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    courses = result.scalars().all()

    logger.info(f"Found {total} courses, returning page {page}")

    return CourseListResponse(
        items=[_serialize_course(c) for c in courses],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{course_id}", response_model=CourseResponse, dependencies=[Depends(audit_access)])
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    Get course details by ID
    """
    logger.info(f"Getting course {course_id} for user {current_user.id}")

    query = select(Course).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    return _serialize_course(course)


@router.put("/{course_id}", response_model=CourseResponse, dependencies=[Depends(audit_access)])
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Update course (Admin only)

    Requires admin role.
    """
    logger.info(f"Updating course {course_id} by user {current_user.id}")

    # Get existing course
    query = select(Course).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    # Update fields
    update_data = course_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field in ['learning_objectives', 'prerequisites', 'tags'] and value is not None:
            setattr(course, field, json.dumps(value))
        else:
            setattr(course, field, value)

    await db.commit()
    await db.refresh(course)

    logger.info(f"Course {course_id} updated successfully")
    return _serialize_course(course)


@router.delete("/{course_id}", dependencies=[Depends(audit_access)])
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Delete course (Admin only)

    Requires admin role. This will also delete all associated tasks.
    """
    logger.info(f"Deleting course {course_id} by user {current_user.id}")

    # Get existing course
    query = select(Course).where(Course.id == course_id)
    result = await db.execute(query)
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    await db.delete(course)
    await db.commit()

    logger.info(f"Course {course_id} deleted successfully")
    return {"status": "success", "message": f"Course {course_id} deleted"}


@router.get("/{course_id}/tasks", response_model=List[TaskSummary], dependencies=[Depends(audit_access)])
async def get_course_tasks(
    course_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    Get all tasks for a course
    """
    logger.info(f"Getting tasks for course {course_id}")

    # Verify course exists
    course_query = select(Course).where(Course.id == course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    # Get tasks
    query = select(Task).where(Task.course_id == course_id).order_by(Task.order)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        TaskSummary(
            id=task.id,
            title=task.title,
            task_type=task.task_type,
            status=task.status.value,
            order=task.order,
            points=task.points
        )
        for task in tasks
    ]
