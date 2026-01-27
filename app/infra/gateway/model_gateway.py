import logging
from typing import Any, Dict, List, Optional
from app.infra.gateway.schemas import ModelCall, ModelConfig, RoutingContext

logger = logging.getLogger(__name__)

class ModelGateway:
    """
    Unified Gateway for LLM Calls.
    Handles routing, retries, and cost tracking.
    """
    
    def __init__(self, budget_manager=None):
        self.budget_manager = budget_manager

    async def call(self, call: ModelCall, context: RoutingContext) -> str:
        """
        Execute an LLM call with routing and safety.
        """
        logger.info(f"Calling model for agent: {context.agent_type}")
        
        # Mock call logic
        if self.budget_manager:
            await self.budget_manager.track_cost(context.session_id, 0.001)
            
        return "This is a mock response from ModelGateway."

    async def stream_call(self, call: ModelCall, context: RoutingContext):
        """
        Execute a streaming LLM call.
        """
        logger.info(f"Streaming call for agent: {context.agent_type}")
        yield "Mock "
        yield "stream "
        yield "response."
