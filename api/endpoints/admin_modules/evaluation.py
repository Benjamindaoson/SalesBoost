"""
Admin API - Evaluation Configuration
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
from models.evaluation_models import EvaluationDimension

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
class EvaluationDimensionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weight: float = 1.0
    applicable_stages: List[str] = []
    criteria_prompt: Optional[str] = None
    is_active: bool = True

class EvaluationDimensionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weight: Optional[float] = None
    applicable_stages: Optional[List[str]] = None
    criteria_prompt: Optional[str] = None
    is_active: Optional[bool] = None

class EvaluationDimensionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    weight: float
    applicable_stages: List[str]
    criteria_prompt: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True

# Routes
@router.post("", response_model=EvaluationDimensionResponse)
async def create_dimension(
    dimension: EvaluationDimensionCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """创建评估维度"""
    db_dimension = EvaluationDimension(
        id=str(uuid.uuid4()),
        name=dimension.name,
        description=dimension.description,
        weight=dimension.weight,
        applicable_stages=dimension.applicable_stages, # Pydantic list -> JSON
        criteria_prompt=dimension.criteria_prompt,
        is_active=dimension.is_active
    )
    db.add(db_dimension)
    await db.commit()
    await db.refresh(db_dimension)
    return db_dimension

@router.get("", response_model=List[EvaluationDimensionResponse])
async def list_dimensions(
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """列出所有评估维度"""
    result = await db.execute(select(EvaluationDimension))
    return result.scalars().all()

@router.get("/{dimension_id}", response_model=EvaluationDimensionResponse)
async def get_dimension(
    dimension_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """获取维度详情"""
    result = await db.execute(select(EvaluationDimension).where(EvaluationDimension.id == dimension_id))
    dimension = result.scalar_one_or_none()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return dimension

@router.put("/{dimension_id}", response_model=EvaluationDimensionResponse)
async def update_dimension(
    dimension_id: str,
    dimension_update: EvaluationDimensionUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """更新评估维度"""
    result = await db.execute(select(EvaluationDimension).where(EvaluationDimension.id == dimension_id))
    dimension = result.scalar_one_or_none()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    update_data = dimension_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dimension, key, value)
    
    await db.commit()
    await db.refresh(dimension)
    return dimension

@router.delete("/{dimension_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dimension(
    dimension_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """删除评估维度"""
    result = await db.execute(select(EvaluationDimension).where(EvaluationDimension.id == dimension_id))
    dimension = result.scalar_one_or_none()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    await db.delete(dimension)
    await db.commit()
    return None
