"""
Admin API - Scenarios
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
from models.config_models import ScenarioConfig

router = APIRouter()

# 权限依赖
async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username != "admin": 
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

# Models
class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    course_id: str
    difficulty_level: str
    product_category: str
    max_turns: int = 10
    is_active: bool = True

class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty_level: Optional[str] = None
    product_category: Optional[str] = None
    max_turns: Optional[int] = None
    is_active: Optional[bool] = None

class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    course_id: str
    difficulty_level: str
    product_category: str
    max_turns: int
    is_active: bool
    
    class Config:
        from_attributes = True

# Routes
@router.post("", response_model=ScenarioResponse)
async def create_scenario(
    scenario: ScenarioCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """创建新场景"""
    db_scenario = ScenarioConfig(
        id=str(uuid.uuid4()),
        name=scenario.name,
        description=scenario.description,
        course_id=scenario.course_id,
        difficulty_level=scenario.difficulty_level,
        product_category=scenario.product_category,
        max_turns=scenario.max_turns,
        is_active=scenario.is_active
    )
    db.add(db_scenario)
    await db.commit()
    await db.refresh(db_scenario)
    return db_scenario

@router.get("", response_model=List[ScenarioResponse])
async def list_scenarios(
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """列出所有场景"""
    result = await db.execute(select(ScenarioConfig))
    return result.scalars().all()

@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """获取场景详情"""
    result = await db.execute(select(ScenarioConfig).where(ScenarioConfig.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    scenario_update: ScenarioUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """更新场景"""
    result = await db.execute(select(ScenarioConfig).where(ScenarioConfig.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    update_data = scenario_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(scenario, key, value)
    
    await db.commit()
    await db.refresh(scenario)
    return scenario

@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """删除场景"""
    result = await db.execute(select(ScenarioConfig).where(ScenarioConfig.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    await db.delete(scenario)
    await db.commit()
    return None
