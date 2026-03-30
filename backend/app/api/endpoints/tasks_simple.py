"""
Simplified Tasks API - Direct implementation without complex dependencies
"""
import logging
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...models.task import Task as TaskModel, TaskStatus
from ...models.course import Course

logger = logging.getLogger(__name__)
router = APIRouter()


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    task_type: str
    status: str
    order: int
    points: int
    passing_score: float
    time_limit_minutes: int | None
    course_id: int

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all tasks
    """
    logger.info("Fetching all tasks")

    query = select(TaskModel).order_by(TaskModel.order)
    result = await db.execute(query)
    tasks = result.scalars().all()

    logger.info(f"Found {len(tasks)} tasks")

    return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get a specific task by ID
    """
    logger.info(f"Fetching task {task_id}")

    query = select(TaskModel).where(TaskModel.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse.model_validate(task)
