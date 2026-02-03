"""
Scenarios API Endpoints
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session
from api.deps import require_user
from models.config_models import ScenarioConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenarios", tags=["scenarios"], dependencies=[Depends(require_user)])


class PersonaResponse(BaseModel):
    """人设响应"""
    id: str
    name: str
    occupation: Optional[str]
    age_range: Optional[str]
    personality_traits: Optional[str]
    communication_style: Optional[str]
    difficulty_level: str
    
    class Config:
        from_attributes = True


class ScenarioResponse(BaseModel):
    """场景响应"""
    id: str
    course_id: str
    name: str
    description: Optional[str]
    product_category: str
    difficulty_level: str
    max_turns: int
    personas: List[PersonaResponse]
    
    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """场景列表响应"""
    items: List[ScenarioResponse]
    total: int


@router.get("", response_model=ScenarioListResponse)
async def list_scenarios(
    course_id: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """获取场景列表"""
    query = select(ScenarioConfig).where(ScenarioConfig.is_active == True)
    
    if course_id:
        query = query.where(ScenarioConfig.course_id == course_id)
    if difficulty:
        query = query.where(ScenarioConfig.difficulty_level == difficulty)
    
    result = await db.execute(query)
    scenarios = result.scalars().all()
    
    return ScenarioListResponse(
        items=scenarios,
        total=len(scenarios),
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取场景详情"""
    result = await db.execute(
        select(ScenarioConfig).where(ScenarioConfig.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenario
