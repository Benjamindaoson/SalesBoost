"""
Admin API - Personas
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
from models.config_models import CustomerPersona

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
class PersonaCreate(BaseModel):
    name: str
    occupation: str
    age_range: str
    personality_traits: str
    communication_style: str
    difficulty_level: str
    tags: List[str] = []

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    occupation: Optional[str] = None
    age_range: Optional[str] = None
    personality_traits: Optional[str] = None
    communication_style: Optional[str] = None
    difficulty_level: Optional[str] = None
    tags: Optional[List[str]] = None

class PersonaResponse(BaseModel):
    id: str
    name: str
    occupation: str
    age_range: Optional[str]
    personality_traits: Optional[str]
    communication_style: Optional[str]
    difficulty_level: str
    tags: List[str]
    
    class Config:
        from_attributes = True

# Routes
@router.post("", response_model=PersonaResponse)
async def create_persona(
    persona: PersonaCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """创建新人设"""
    db_persona = CustomerPersona(
        id=str(uuid.uuid4()),
        name=persona.name,
        occupation=persona.occupation,
        age_range=persona.age_range,
        personality_traits=persona.personality_traits,
        communication_style=persona.communication_style,
        difficulty_level=persona.difficulty_level,
        tags=persona.tags
    )
    db.add(db_persona)
    await db.commit()
    await db.refresh(db_persona)
    return db_persona

@router.get("", response_model=List[PersonaResponse])
async def list_personas(
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """列出所有人设"""
    result = await db.execute(select(CustomerPersona))
    return result.scalars().all()

@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """获取人设详情"""
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona

@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    persona_update: PersonaUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """更新人设"""
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    update_data = persona_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(persona, key, value)
    
    await db.commit()
    await db.refresh(persona)
    return persona

@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: str,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_current_admin)
):
    """删除人设"""
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    await db.delete(persona)
    await db.commit()
    return None
