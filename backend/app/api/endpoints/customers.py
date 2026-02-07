
# Customers API Endpoints - Customer Persona Management
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...api.deps import audit_access, require_user
from ...api.auth_schemas import UserSchema as User
from ...models.config_models import CustomerPersona

logger = logging.getLogger(__name__)
router = APIRouter(tags=["customers"], dependencies=[Depends(require_user), Depends(audit_access)])


class CustomerCreate(BaseModel):
    name: str
    age: int
    job: str
    traits: List[str]
    description: Optional[str] = None
    avatar_color: str = "from-blue-200 to-blue-400"
    scenario_id: str # Required to link to a scenario


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    job: Optional[str] = None
    traits: Optional[List[str]] = None
    avatar_color: Optional[str] = None
    description: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    age: int
    job: str
    traits: List[str]
    description: str
    creator: str
    rehearsal_count: int
    last_rehearsal_time: str
    avatar_color: str

    class Config:
        from_attributes = True

def map_persona_to_response(persona: CustomerPersona) -> CustomerResponse:
    # Map DB fields to Frontend fields
    try:
        age = int(persona.age_range) if persona.age_range and persona.age_range.isdigit() else 30
    except:
        age = 30 # Default
    
    traits = []
    if persona.personality_traits:
        traits = [t.strip() for t in persona.personality_traits.split(',') if t.strip()]
        
    return CustomerResponse(
        id=persona.id,
        name=persona.name,
        age=age,
        job=persona.occupation or "Unknown",
        traits=traits,
        description=f"{age}岁 · {persona.occupation or 'Unknown'} · {', '.join(traits[:2])}",
        creator="System", # DB doesn't track creator name directly yet
        rehearsal_count=0, # Placeholder
        last_rehearsal_time="Recently", # Placeholder
        avatar_color="from-blue-200 to-blue-400" # Placeholder
    )

@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """
    Get all customer personas
    """
    result = await db.execute(select(CustomerPersona))
    personas = result.scalars().all()
    return [map_persona_to_response(p) for p in personas]

@router.post("", response_model=CustomerResponse)
async def create_customer(
    customer: CustomerCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """Create a new customer persona"""
    # Map frontend fields to DB fields
    db_persona = CustomerPersona(
        id=str(uuid.uuid4()),
        scenario_id=customer.scenario_id,
        name=customer.name,
        occupation=customer.job,
        age_range=str(customer.age),
        personality_traits=",".join(customer.traits),
        # other fields default
    )
    db.add(db_persona)
    await db.commit()
    await db.refresh(db_persona)
    return map_persona_to_response(db_persona)

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == customer_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Customer not found")
    return map_persona_to_response(persona)

@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_update: CustomerUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    """Update a customer persona"""
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == customer_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Customer not found")

    if customer_update.name is not None:
        persona.name = customer_update.name
    if customer_update.age is not None:
        persona.age_range = str(customer_update.age)
    if customer_update.job is not None:
        persona.occupation = customer_update.job
    if customer_update.traits is not None:
        persona.personality_traits = ",".join(customer_update.traits)
    
    await db.commit()
    await db.refresh(persona)
    return map_persona_to_response(persona)

@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_user)
):
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == customer_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    await db.delete(persona)
    await db.commit()
    return {"message": "Customer deleted"}
