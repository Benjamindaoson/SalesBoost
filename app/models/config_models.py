from pydantic import BaseModel
from typing import Optional

class CustomerPersona(BaseModel):
    name: str
    occupation: str
    personality_traits: str
    pain_points: Optional[str] = None
    goals: Optional[str] = None
