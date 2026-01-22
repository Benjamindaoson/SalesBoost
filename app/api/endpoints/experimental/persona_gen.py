"""
Persona Generator (E2)
基于 LLM 生成客户人设
"""
import logging
from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

class PersonaGenerateRequest(BaseModel):
    industry: str
    role: str
    company_size: Optional[str] = "Mid-market"
    pain_points: Optional[str] = None # 用户提供的痛点描述

class PersonaGenerateResponse(BaseModel):
    name: str
    occupation: str
    age: int
    personality_traits: list[str]
    communication_style: str
    pain_points: list[str]
    buying_motivation: str
    initial_mood: str

@router.post("/generate", response_model=PersonaGenerateResponse)
async def generate_persona(req: PersonaGenerateRequest):
    """
    Mock: 生成人设
    实际应调用 LLM (GPT-4) 根据 prompt 生成 JSON
    """
    logger.info(f"Generating persona for {req.role} in {req.industry}")
    
    return PersonaGenerateResponse(
        name="Alex Chen",
        occupation=f"{req.role} at {req.company_size} Tech Corp",
        age=35,
        personality_traits=["Direct", "Analytical", "Skeptical"],
        communication_style="Professional and concise",
        pain_points=[
            "Current solution is too slow",
            "Budget cuts in Q3",
            "Compliance issues"
        ],
        buying_motivation="Efficiency and ROI",
        initial_mood="neutral"
    )
