import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass

from app.engine.intent.intent_classifier import IntentGateway
from app.agents.practice.npc_simulator import NPCGenerator
from app.agents.ask.coach_agent import SalesCoachAgent
from app.observability.tracing.execution_tracer import trace_manager
from app.infra.gateway.model_gateway import ModelGateway
from app.infra.guardrails.streaming_guard import streaming_guard
from app.schemas.fsm import FSMState, SalesStage

logger = logging.getLogger(__name__)

@dataclass
class NPCReply:
    response: str
    mood_after: float

@dataclass
class TurnResult:
    turn_number: int
    npc_reply: NPCReply
    ttfs_ms: float
    coach_advice: Optional[Any] = None

@dataclass
class DummyCoordinator:
    session_id: str = "default"
    user_id: str = "default"
    fsm_state: Optional[Any] = None

class WorkflowCoordinator:
    """
    Production-Ready Workflow Coordinator.
    Orchestrates the cognitive flow: Intent -> NPC -> Coach.
    """
    
    def __init__(
        self, 
        model_gateway: ModelGateway,
        budget_manager: Any,
        session_director: Any,
        persona: Any,
        **kwargs
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        self.session_director = session_director
        self.persona = persona
        self.coordinator = DummyCoordinator()
        
        self.intent_gateway = IntentGateway()
        self.npc_agent = NPCGenerator()
        self.coach_agent = SalesCoachAgent()
        
        self.fsm_state = FSMState(current_stage=SalesStage.OPENING, turn_count=0, npc_mood=0.5)
        self.session_id = "default"
        self.user_id = "default"

    def initialize_session(self, session_id: str, user_id: str, state: FSMState) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.fsm_state = state

    async def execute_turn(self, turn_number: int, user_message: str) -> TurnResult:
        """Execute a full turn: Intent -> NPC -> Coach."""
        start_time = time.time()
        trace_id = f"{self.session_id}_{turn_number}"
        
        trace_manager.start_trace(trace_id, session_id=self.session_id, user_id=self.user_id)
        
        try:
            # 1. Perception: Intent Detection
            intent_result = await self.intent_gateway.classify(user_message, {})
            
            # 2. Fast Path: NPC Response
            npc_resp = await self.npc_agent.generate_response(
                user_message, [], self.persona, self.fsm_state.current_stage
            )
            
            ttfs = (time.time() - start_time) * 1000
            
            # 3. Slow Path: Coach Advice
            coach_advice = await self.coach_agent.get_advice(
                history=[{"role": "sales", "content": user_message}],
                session_id=self.session_id,
                turn_number=turn_number
            )
            
            # Update state
            self.fsm_state.turn_count += 1
            if intent_result.stage_suggestion:
                self.fsm_state.current_stage = intent_result.stage_suggestion
            
            trace_manager.complete_trace(trace_id)
            
            return TurnResult(
                turn_number=turn_number,
                npc_reply=NPCReply(response=npc_resp.content, mood_after=npc_resp.mood),
                ttfs_ms=ttfs,
                coach_advice=coach_advice
            )
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}")
            trace_manager.complete_trace(trace_id, error=str(e))
            raise

    async def execute_turn_stream(
        self,
        turn_number: int,
        user_message: str,
        db: Any = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streamed version of execute_turn with security auditing."""
        
        intent_result = await self.intent_gateway.classify(user_message, {})
        
        async def mock_npc_stream():
            yield "As "
            yield "a "
            yield "customer, "
            yield "I'm "
            yield "listening."
            
        audited_stream = streaming_guard.audit_stream(mock_npc_stream())
        
        async for chunk in audited_stream:
            yield {
                "type": "npc_chunk",
                "content": chunk
            }
            
        coach_advice = await self.coach_agent.get_advice(
            history=[{"role": "sales", "content": user_message}],
            session_id=self.session_id,
            turn_number=turn_number
        )
        
        yield {
            "type": "coach_advice",
            "advice": coach_advice.dict() if hasattr(coach_advice, 'dict') else coach_advice
        }
