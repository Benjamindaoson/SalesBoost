"""
Task Management API

Provides CRUD operations for tasks.
"""

import json
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from api.deps import require_user, require_admin, audit_access
from api.auth_schemas import UserSchema as User
from app.models.task import Task, TaskStatus
from app.models.course import Course
from app.models.session import Session as TrainingSession

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Schemas ====================

class TaskCreate(BaseModel):
    """Schema for creating a task"""
    course_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    task_type: str = Field(..., pattern="^(conversation|quiz|simulation)$")
    status: TaskStatus = TaskStatus.LOCKED
    order: int = 0
    points: int = 100
    passing_score: float = Field(default=70.0, ge=0, le=100)
    time_limit_minutes: Optional[int] = None
    instructions: Optional[str] = None
    scenario: Optional[dict] = None
    customer_profile: Optional[dict] = None


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    task_type: Optional[str] = Field(None, pattern="^(conversation|quiz|simulation)$")
    status: Optional[TaskStatus] = None
    order: Optional[int] = None
    points: Optional[int] = None
    passing_score: Optional[float] = Field(None, ge=0, le=100)
    time_limit_minutes: Optional[int] = None
    instructions: Optional[str] = None
    scenario: Optional[dict] = None
    customer_profile: Optional[dict] = None


class TaskResponse(BaseModel):
    """Schema for task response"""
    id: int
    course_id: int
    title: str
    description: Optional[str]
    task_type: str
    status: str
    order: int
    points: int
    passing_score: float
    time_limit_minutes: Optional[int]
    instructions: Optional[str]
    scenario: Optional[dict]
    customer_profile: Optional[dict]
    created_at: str
    updated_at: str
    completion_rate: Optional[float] = None
    average_score: Optional[float] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for paginated task list"""
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int


class TaskStartResponse(BaseModel):
    """Response when starting a task"""
    session_id: str
    task_id: int
    message: str


# ==================== Helper Functions ====================

async def _calculate_task_stats(task_id: int, db: AsyncSession) -> tuple[Optional[float], Optional[float]]:
    """Calculate completion rate and average score for a task"""
    # Get all sessions for this task
    query = select(TrainingSession).where(TrainingSession.task_id == task_id)
    result = await db.execute(query)
    sessions = result.scalars().all()

    if not sessions:
        return None, None

    total_sessions = len(sessions)
    completed_sessions = len([s for s in sessions if s.status == "completed"])
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0

    # Calculate average score
    scores = [s.final_score for s in sessions if s.final_score is not None]
    average_score = sum(scores) / len(scores) if scores else None

    return round(completion_rate, 2), round(average_score, 2) if average_score else None


def _serialize_task(task: Task, completion_rate: Optional[float] = None, average_score: Optional[float] = None) -> TaskResponse:
    """Convert Task model to TaskResponse"""
    return TaskResponse(
        id=task.id,
        course_id=task.course_id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=task.status.value,
        order=task.order,
        points=task.points,
        passing_score=task.passing_score,
        time_limit_minutes=task.time_limit_minutes,
        instructions=task.instructions,
        scenario=json.loads(task.scenario) if task.scenario else None,
        customer_profile=json.loads(task.customer_profile) if task.customer_profile else None,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        completion_rate=completion_rate,
        average_score=average_score
    )


# ==================== API Endpoints ====================

@router.post("", response_model=TaskResponse, dependencies=[Depends(audit_access)])
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Create a new task (Admin only)

    Requires admin role.
    """
    logger.info(f"Creating task: {task_data.title} by user {current_user.id}")

    # Verify course exists
    course_query = select(Course).where(Course.id == task_data.course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail=f"Course {task_data.course_id} not found")

    # Create task
    task = Task(
        course_id=task_data.course_id,
        title=task_data.title,
        description=task_data.description,
        task_type=task_data.task_type,
        status=task_data.status,
        order=task_data.order,
        points=task_data.points,
        passing_score=task_data.passing_score,
        time_limit_minutes=task_data.time_limit_minutes,
        instructions=task_data.instructions,
        scenario=json.dumps(task_data.scenario) if task_data.scenario else None,
        customer_profile=json.dumps(task_data.customer_profile) if task_data.customer_profile else None
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"Task created successfully: {task.id}")
    return _serialize_task(task)


@router.get("", response_model=TaskListResponse, dependencies=[Depends(audit_access)])
async def list_tasks(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    List tasks with filtering and pagination

    Available filters:
    - course_id: filter by course
    - task_type: conversation, quiz, simulation
    - status: locked, available, in_progress, completed
    """
    logger.info(f"Listing tasks for user {current_user.id}")

    # Build query
    query = select(Task)

    # Apply filters
    if course_id:
        query = query.where(Task.course_id == course_id)

    if task_type:
        query = query.where(Task.task_type == task_type)

    if status:
        try:
            status_enum = TaskStatus(status)
            query = query.where(Task.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Task.order, Task.created_at).offset(offset).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Calculate stats for each task
    task_responses = []
    for task in tasks:
        completion_rate, average_score = await _calculate_task_stats(task.id, db)
        task_responses.append(_serialize_task(task, completion_rate, average_score))

    logger.info(f"Found {total} tasks, returning page {page}")

    return TaskListResponse(
        items=task_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{task_id}", response_model=TaskResponse, dependencies=[Depends(audit_access)])
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    Get task details by ID
    """
    logger.info(f"Getting task {task_id} for user {current_user.id}")

    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Calculate stats
    completion_rate, average_score = await _calculate_task_stats(task_id, db)

    return _serialize_task(task, completion_rate, average_score)


@router.put("/{task_id}", response_model=TaskResponse, dependencies=[Depends(audit_access)])
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Update task (Admin only)

    Requires admin role.
    """
    logger.info(f"Updating task {task_id} by user {current_user.id}")

    # Get existing task
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Update fields
    update_data = task_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field in ['scenario', 'customer_profile'] and value is not None:
            setattr(task, field, json.dumps(value))
        else:
            setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    logger.info(f"Task {task_id} updated successfully")

    # Calculate stats
    completion_rate, average_score = await _calculate_task_stats(task_id, db)

    return _serialize_task(task, completion_rate, average_score)


@router.delete("/{task_id}", dependencies=[Depends(audit_access)])
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)
):
    """
    Delete task (Admin only)

    Requires admin role. This will also delete all associated sessions.
    """
    logger.info(f"Deleting task {task_id} by user {current_user.id}")

    # Get existing task
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    await db.delete(task)
    await db.commit()

    logger.info(f"Task {task_id} deleted successfully")
    return {"status": "success", "message": f"Task {task_id} deleted"}


@router.post("/{task_id}/start", response_model=TaskStartResponse, dependencies=[Depends(audit_access)])
async def start_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    Start a task (create a new training session)

    This creates a new session for the user to begin the task.
    """
    logger.info(f"Starting task {task_id} for user {current_user.id}")

    # Get task
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if task is available
    if task.status == TaskStatus.LOCKED:
        raise HTTPException(status_code=403, detail="This task is locked. Complete prerequisites first.")

    # Create new session
    session_id = str(uuid.uuid4())
    session = TrainingSession(
        session_id=session_id,
        user_id=current_user.id,
        task_id=task_id,
        course_id=task.course_id,
        status="active",
        turns_count=0
    )

    db.add(session)
    await db.commit()

    logger.info(f"Session {session_id} created for task {task_id}")

    return TaskStartResponse(
        session_id=session_id,
        task_id=task_id,
        message=f"Task '{task.title}' started successfully"
    )
