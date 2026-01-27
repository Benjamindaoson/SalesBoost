import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.agents.roles.base import BaseAgent

logger = logging.getLogger(__name__)

class NPCResponse(BaseModel):
    content: str
    mood: float
    next_stage_hint: Optional[str] = None

class NPCGenerator(BaseAgent):
    """
    NPC Simulator Agent.
    Simulates a customer responding to sales pitches.
    """
    
    async def generate_response(
        self, 
        message: str, 
        history: List[Dict[str, str]], 
        persona: Any,
        stage: str
    ) -> NPCResponse:
        logger.info(f"Generating NPC response for stage: {stage}")
        
        # Simple mock logic
        response_text = f"As a {persona.name if hasattr(persona, 'name') else 'customer'}, I hear you. Tell me more about how this fits my needs."
        if "price" in message.lower():
            response_text = "The price seems a bit high for our current budget."
            
        return NPCResponse(
            content=response_text,
            mood=0.5,
            next_stage_hint=stage
        )
