"""
Simplified Statistics API
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...models.task import Task, TaskStatus
from ...models.session import Session as TrainingSession

logger = logging.getLogger(__name__)
router = APIRouter()


class StatisticsResponse(BaseModel):
    """统计数据响应"""
    totalTasks: int
    inProgress: int
    completed: int
    averageScore: float
    lockedItems: int


@router.get("", response_model=StatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取统计数据
    """
    logger.info("Getting statistics")

    # 查询所有任务
    tasks_query = select(Task)
    tasks_result = await db.execute(tasks_query)
    tasks = tasks_result.scalars().all()

    # 查询所有会话
    sessions_query = select(TrainingSession)
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()

    # 计算统计数据
    total_tasks = len(tasks)
    locked_items = len([t for t in tasks if t.status == TaskStatus.LOCKED])

    # 统计进行中和已完成的会话
    in_progress = len([s for s in sessions if s.status.value == "active"])
    completed = len([s for s in sessions if s.status.value == "completed"])

    # 计算平均分数
    scores = [s.score for s in sessions if s.score is not None]
    average_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    logger.info(f"Statistics: total={total_tasks}, in_progress={in_progress}, completed={completed}, avg_score={average_score}")

    return StatisticsResponse(
        totalTasks=total_tasks,
        inProgress=in_progress,
        completed=completed,
        averageScore=average_score,
        lockedItems=locked_items
    )
