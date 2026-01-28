import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.agents.roles.base import BaseAgent

logger = logging.getLogger(__name__)

class NPCResponse(BaseModel):
    content: str
    mood: float
class NPCGenerator(BaseAgent):
    """
    NPC Simulator Agent.
    Simulates a customer responding to sales pitches.
    """
    
    def __init__(self, model_gateway=None):
        super().__init__()
        self.gateway = model_gateway

    async def generate_response(
        self, 
        message: str, 
        history: List[Dict[str, str]], 
        persona: Any,
        stage: str
    ) -> NPCResponse:
        logger.info(f"Generating NPC response for stage: {stage}")
        
        if not self.gateway:
            logger.warning("No ModelGateway provided, falling back to basic mock")
            return NPCResponse(
                content="[System: LLM Gateway unavailable] I hear you.",
                mood=0.5
            )

        # Construct System Prompt
        persona_desc = getattr(persona, 'description', 'A typical customer')
        persona_obj = getattr(persona, 'objections', [])
        
        sys_prompt = f"""You are a roleplay customer in a sales training simulation.
Persona: {persona_desc}
Objections: {', '.join(persona_obj) if persona_obj else 'Price, Timing'}
Stage: {stage}

Your goal is to react realistically to the salesperson.
Output strictly JSON format:
{{
  "content": "your verbal response",
  "mood": 0.0 to 1.0 (float),
  "next_stage_hint": "optional hint"
}}
"""
        
        # User Message
        user_prompt = f"Salesperson says: {message}"

        # Call Gateway
        from app.infra.gateway.schemas import ModelCall, RoutingContext, AgentType, LatencyMode
        
        call_ctx = RoutingContext(
            agent_type=AgentType.NPC,
            turn_importance=0.5,
            risk_level="low",
            budget_remaining=10.0,
            latency_mode=LatencyMode.FAST,
            retrieval_confidence=None,
            turn_number=len(history),
            session_id="sim-session",
            budget_authorized=True
        )
        
        try:
            raw_response = await self.gateway.call(
                ModelCall(prompt=user_prompt, system_prompt=sys_prompt), 
                call_ctx
            )
            
            # Simple simulation of JSON parsing/mock return for now since Gateway is still mock
            # In real impl, we'd parse json.loads(raw_response)
            # For this audit fix, we are trusting the Gateway updates below to return valid text/json
            
            # If the gateway returns the old mock string, we handle it
            if "mock response" in raw_response.lower() or "{" not in raw_response:
                 return NPCResponse(content=raw_response, mood=0.5)

            import json
            try:
                data = json.loads(raw_response)
                return NPCResponse(**data)
            except json.JSONDecodeError:
                 return NPCResponse(content=raw_response, mood=0.5)
                 
        except Exception as e:
            logger.error(f"NPC Generation failed: {e}")
            return NPCResponse(content="[System Error] Let's continue.", mood=0.5)
