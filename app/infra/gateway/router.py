from typing import Dict, Optional, Union
from app.infra.gateway.schemas import AgentType, LatencyMode, RoutingContext
from core.llm_context import LLMCallContext

AGENT_TYPE_MAP: Dict[str, AgentType] = {
    "intent_gate": AgentType.INTENT_GATE,
    "npc": AgentType.NPC,
    "npc_generator": AgentType.NPC_GENERATOR,
    "coach": AgentType.COACH,
    "coach_generator": AgentType.COACH_GENERATOR,
    "evaluator": AgentType.EVALUATOR,
    "rag": AgentType.RAG,
    "retriever": AgentType.RETRIEVER,
    "compliance": AgentType.COMPLIANCE,
    "session_director": AgentType.SESSION_DIRECTOR,
    "adoption_tracker": AgentType.ADOPTION_TRACKER,
    "strategy": AgentType.STRATEGY,
}

def resolve_agent_type(agent_type: Union[str, AgentType]) -> AgentType:
    if isinstance(agent_type, AgentType):
        return agent_type
    key = (agent_type or "").strip().lower()
    return AGENT_TYPE_MAP.get(key, AgentType.COACH_GENERATOR)

def build_routing_context(
    agent_type: Union[str, AgentType],
    llm_context: Optional[LLMCallContext],
) -> RoutingContext:
    context = llm_context or LLMCallContext(session_id="default", turn_number=1)
    latency_mode = LatencyMode.FAST if context.latency_mode.lower() == "fast" else LatencyMode.SLOW
    return RoutingContext(
        agent_type=resolve_agent_type(agent_type),
        turn_importance=context.turn_importance,
        risk_level=context.risk_level,
        budget_remaining=context.budget_remaining,
        latency_mode=latency_mode,
        retrieval_confidence=context.retrieval_confidence,
        turn_number=context.turn_number,
        session_id=context.session_id,
        budget_authorized=context.budget_authorized,
    )

class ModelRouter:
    """Unified Model Router for all agents."""
    def route(self, context: RoutingContext):
        # Implementation of routing logic (e.g. Rulebook based)
        pass
