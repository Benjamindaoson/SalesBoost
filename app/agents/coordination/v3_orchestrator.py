"""
V3 Orchestrator - fast/slow path execution.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.v3.adoption_tracker_v3 import AdoptionTrackerV3
from app.agents.v3.coach_generator_v3 import CoachGeneratorV3
from app.agents.v3.evaluator_v3 import EvaluatorV3
from app.agents.v3.npc_generator_v3 import NPCGeneratorV3
from app.agents.v3.retriever_v3 import RetrieverV3
from app.agents.v3.session_director_v3 import SessionDirectorV3
from app.models.config_models import CustomerPersona
from app.schemas.fsm import FSMState
from app.schemas.trace import AgentDecision, CallType
from app.schemas.v3_agent_outputs import (
    AdoptionLog,
    CoachAdvice,
    EvidencePack,
    FastPathResult,
    NpcReply,
    SlowPathResult,
    TurnPlan,
    V3TurnResult,
)
from app.security.runtime_guard import SecurityAction, runtime_guard
from app.services.context_engine import ContextBuilder
from app.services.knowledge_engine import knowledge_engine
from app.services.model_gateway import AgentType, LatencyMode, ModelGateway, RoutingContext
from app.services.model_gateway.budget import BudgetManager
from app.services.observability import trace_manager
from app.services.state.wal import wal_manager

logger = logging.getLogger(__name__)


class V3Orchestrator:
    """V3 Orchestrator with explicit execute_turn API."""

    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
        session_director: SessionDirectorV3,
        persona: CustomerPersona,
        retriever: Optional[RetrieverV3] = None,
        npc_generator: Optional[NPCGeneratorV3] = None,
        coach_generator: Optional[CoachGeneratorV3] = None,
        evaluator: Optional[EvaluatorV3] = None,
        adoption_tracker: Optional[AdoptionTrackerV3] = None,
    ) -> None:
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        self.session_director = session_director
        self.persona = persona

        self.retriever = retriever or RetrieverV3(model_gateway, budget_manager)
        self.npc_generator = npc_generator or NPCGeneratorV3(model_gateway, budget_manager, persona)
        self.coach_generator = coach_generator or CoachGeneratorV3(model_gateway, budget_manager)
        self.evaluator = evaluator or EvaluatorV3(model_gateway, budget_manager)
        self.adoption_tracker = adoption_tracker or AdoptionTrackerV3(model_gateway, budget_manager)

        self.fsm_state: Optional[FSMState] = None
        self.conversation_history: list[Dict[str, Any]] = []
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None

        self.metrics = {
            "fast_path_ttfs_ms": [],
            "slow_path_total_ms": [],
            "provider_hits": {},
            "model_hits": {},
            "downgrade_count": 0,
            "downgrade_reasons": [],
            "token_usage": [],
            "estimated_costs": [],
        }
        self._last_slow_task: Optional[asyncio.Task] = None

    def initialize_session(self, session_id: str, user_id: str, fsm_state: FSMState) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.fsm_state = fsm_state
        self.conversation_history = []
        self.budget_manager.initialize_session(session_id)
        logger.info("V3 Orchestrator initialized: %s", session_id)

    async def execute_turn_stream(
        self,
        turn_number: int,
        user_message: str,
        db: Optional[AsyncSession] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a turn with streaming response.
        Yields:
            {"type": "token", "content": "..."}
            {"type": "result", "data": V3TurnResult}
            {"type": "error", "message": "..."}
        """
        if not self.fsm_state or not self.session_id:
            raise RuntimeError("Session not initialized")

        # WAL: Log User Input
        state_dict = self.fsm_state.dict() if hasattr(self.fsm_state, "dict") else str(self.fsm_state)
        await wal_manager.log_event(
            self.session_id, 
            turn_number, 
            "USER_INPUT", 
            {"message": user_message, "fsm_state": state_dict}
        )

        if not self.budget_manager.is_authorized(self.session_id):
            yield {"type": "error", "message": f"Budget not authorized for session: {self.session_id}"}
            return

        self.budget_manager.reset_turn_budget(self.session_id)

        self.conversation_history.append(
            {
                "role": "user",
                "content": user_message,
                "turn": turn_number,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        fast_trace_id = trace_manager.start_trace(self.session_id, turn_number, CallType.FAST_PATH)
        
        fast_path_result = None
        try:
            async for chunk in self._execute_fast_path_stream(
                turn_number=turn_number,
                user_message=user_message,
                fast_trace_id=fast_trace_id,
            ):
                if chunk["type"] == "token":
                    yield chunk
                elif chunk["type"] == "result":
                    fast_path_result = chunk["data"]
        except Exception as e:
            logger.error(f"Fast path stream failed: {e}")
            trace_manager.complete_trace(fast_trace_id, status="error", error=str(e))
            yield {"type": "error", "message": str(e)}
            return

        if not fast_path_result:
            yield {"type": "error", "message": "No result from fast path"}
            return

        # WAL: Log Fast Path Result
        await wal_manager.log_event(
            self.session_id,
            turn_number,
            "FAST_PATH_RESULT",
            fast_path_result.dict() if hasattr(fast_path_result, "dict") else str(fast_path_result)
        )

        slow_trace_id = trace_manager.start_trace(self.session_id, turn_number, CallType.SLOW_PATH)
        trace = trace_manager.get_trace(fast_trace_id)
        if trace:
            trace.linked_slow_trace_id = slow_trace_id

        self._last_slow_task = asyncio.create_task(
            self._execute_slow_path_async(
                turn_number=turn_number,
                user_message=user_message,
                npc_reply=fast_path_result.npc_reply,
                slow_trace_id=slow_trace_id,
                fast_trace_id=fast_trace_id,
                db=db,
            )
        )

        self.conversation_history.append(
            {
                "role": "npc",
                "content": fast_path_result.npc_reply.response,
                "turn": turn_number,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        turn_result = V3TurnResult(
            turn_number=turn_number,
            fast_path_result=fast_path_result,
            slow_path_result=None,
            session_id=self.session_id,
            user_id=self.user_id,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        yield {"type": "result", "data": turn_result}

    async def _execute_fast_path_stream(self, turn_number: int, user_message: str, fast_trace_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        from app.schemas.agent_outputs import IntentGateOutput
        
        fast_start = time.time()

        action, sec_event = runtime_guard.check_input(user_message)
        if sec_event:
            trace_manager.record_security_event(fast_trace_id, sec_event)
        if action == SecurityAction.BLOCK:
            trace = trace_manager.get_trace(fast_trace_id)
            if trace:
                trace.ttfs_ms = 0.0
                trace.ttfs_stop_point = "blocked_before_generate"
            trace_manager.complete_trace(fast_trace_id, status="blocked", error=sec_event.reason if sec_event else "blocked")
            raise ValueError(f"Security Alert: {sec_event.reason if sec_event else 'blocked'}")

        retrieval_start = time.time()
        evidences = knowledge_engine.retrieve(user_message, top_k=3)
        for ev in evidences:
            trace_manager.record_evidence(fast_trace_id, ev)
        retrieval_ms = (time.time() - retrieval_start) * 1000
        retrieval_confidence = sum(e.confidence for e in evidences) / len(evidences) if evidences else 0.0
        trace_manager.record_agent_call(
            fast_trace_id,
            AgentDecision(
                agent_name="Retriever",
                action="lightweight_retrieve",
                latency_ms=retrieval_ms,
                reasoning=f"items={len(evidences)}, retrieval_confidence={retrieval_confidence:.2f}",
            ),
        )

        # Using NPCGeneratorV3 for streaming
        # Construct dummy intent result as we are skipping IntentGate for now in FastPath
        intent_result = IntentGateOutput(
            detected_intent="general",
            is_aligned=True,
            confidence=1.0,
            alignment_reason="fast_path_skip",
            detected_slots=[],
            missing_slots=[]
        )
        
        npc_start = time.time()
        npc_text_accumulator = []
        npc_reply_result = None
        
        try:
            async for chunk in self.npc_generator.generate_stream(
                user_message=user_message,
                conversation_history=self.conversation_history,
                fsm_state=self.fsm_state,
                intent_result=intent_result,
                session_id=self.session_id,
                turn_number=turn_number,
                retrieval_confidence=retrieval_confidence
            ):
                if chunk["type"] == "token":
                    npc_text_accumulator.append(chunk["content"])
                    yield chunk
                elif chunk["type"] == "result":
                    npc_reply_result = chunk["data"] # NpcReply object
        except Exception as e:
            # Handle stream error
            raise e
            
        npc_latency_ms = (time.time() - npc_start) * 1000
        npc_text = "".join(npc_text_accumulator)
        
        # Post-generation security check (Audit)
        out_action, modified_text, out_event = runtime_guard.check_output(npc_text)
        if out_event:
            trace_manager.record_security_event(fast_trace_id, out_event)
        
        # If text was modified by guard, we should probably update the result
        # But for streaming, the user already saw the tokens. 
        # This is where "Retraction" logic would go in a full system.
        # For now, we just update the record.
        if npc_reply_result:
            npc_reply_result.response = modified_text

        trace_manager.record_agent_call(
            fast_trace_id,
            AgentDecision(
                agent_name="NPC",
                action="generate_stream",
                latency_ms=npc_latency_ms,
                reasoning="npc_stream_completed",
                budget_remaining=self.budget_manager.get_remaining_budget(self.session_id)
            ),
        )
        
        if not npc_reply_result:
             # Fallback if no result yielded
             npc_reply_result = NpcReply(
                response=npc_text,
                mood_before=self.fsm_state.npc_mood,
                mood_after=self.fsm_state.npc_mood,
                mood_change_reason="stream_fallback",
                expressed_signals=[],
                persona_consistency=0.5,
                stage_alignment=True
             )

        evidence_pack = EvidencePack(
            items=[],
            retrieval_mode="lightweight",
            total_items=len(evidences),
            confidence=retrieval_confidence,
            retrieval_time_ms=retrieval_ms,
        )
        
        turn_plan = TurnPlan(
            turn_number=turn_number,
            path_mode="both",
            agents_to_call=["retriever", "npc_generator"],
            budget_allocation={},
            model_upgrade=False,
            risk_level="high" if action == SecurityAction.DOWNGRADE else "low",
            evidence_confidence=retrieval_confidence,
            reasoning="Fast path stream",
        )

        ttfs_ms = (time.time() - fast_start) * 1000
        trace = trace_manager.get_trace(fast_trace_id)
        if trace:
            trace.ttfs_ms = ttfs_ms # Technically TTFS is time to first token, but here we approximate
            trace.ttfs_stop_point = "npc_stream_end"
        trace_manager.complete_trace(fast_trace_id, status="success")

        self.metrics["fast_path_ttfs_ms"].append(ttfs_ms)
        logger.info("Fast Path Stream completed: turn=%s, latency=%.0fms", turn_number, npc_latency_ms)

        result = FastPathResult(
            turn_number=turn_number,
            npc_reply=npc_reply_result,
            evidence_pack=evidence_pack,
            turn_plan=turn_plan,
            ttfs_ms=ttfs_ms,
            total_latency_ms=npc_latency_ms,
        )
        
        yield {"type": "result", "data": result}

    async def execute_turn(
        self,
        turn_number: int,
        user_message: str,
        db: Optional[AsyncSession] = None,
    ) -> V3TurnResult:
        if not self.fsm_state or not self.session_id:
            raise RuntimeError("Session not initialized")
        
        # WAL: Log User Input (Start of Turn)
        # Using .dict() on pydantic model, or manual dict if not pydantic
        state_dict = self.fsm_state.dict() if hasattr(self.fsm_state, "dict") else str(self.fsm_state)
        await wal_manager.log_event(
            self.session_id, 
            turn_number, 
            "USER_INPUT", 
            {"message": user_message, "fsm_state": state_dict}
        )

        if not self.budget_manager.is_authorized(self.session_id):
            raise RuntimeError(f"Budget not authorized for session: {self.session_id}")
        self.budget_manager.reset_turn_budget(self.session_id)

        self.conversation_history.append(
            {
                "role": "user",
                "content": user_message,
                "turn": turn_number,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        fast_trace_id = trace_manager.start_trace(self.session_id, turn_number, CallType.FAST_PATH)
        fast_path_result = await self._execute_fast_path(
            turn_number=turn_number,
            user_message=user_message,
            fast_trace_id=fast_trace_id,
        )

        # WAL: Log Fast Path Result
        await wal_manager.log_event(
            self.session_id,
            turn_number,
            "FAST_PATH_RESULT",
            fast_path_result.dict() if hasattr(fast_path_result, "dict") else str(fast_path_result)
        )

        slow_trace_id = trace_manager.start_trace(self.session_id, turn_number, CallType.SLOW_PATH)
        trace = trace_manager.get_trace(fast_trace_id)
        if trace:
            trace.linked_slow_trace_id = slow_trace_id

        self._last_slow_task = asyncio.create_task(
            self._execute_slow_path_async(
                turn_number=turn_number,
                user_message=user_message,
                npc_reply=fast_path_result.npc_reply,
                slow_trace_id=slow_trace_id,
                fast_trace_id=fast_trace_id,
                db=db,
            )
        )

        self.conversation_history.append(
            {
                "role": "npc",
                "content": fast_path_result.npc_reply.response,
                "turn": turn_number,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return V3TurnResult(
            turn_number=turn_number,
            fast_path_result=fast_path_result,
            slow_path_result=None,
            session_id=self.session_id,
            user_id=self.user_id,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def process_turn(self, turn_number: int, user_message: str, db: Optional[AsyncSession] = None) -> V3TurnResult:
        """Backward compatible wrapper."""
        return await self.execute_turn(turn_number, user_message, db=db)

    async def _execute_fast_path(self, turn_number: int, user_message: str, fast_trace_id: str) -> FastPathResult:
        fast_start = time.time()

        action, sec_event = runtime_guard.check_input(user_message)
        if sec_event:
            trace_manager.record_security_event(fast_trace_id, sec_event)
        if action == SecurityAction.BLOCK:
            trace = trace_manager.get_trace(fast_trace_id)
            if trace:
                trace.ttfs_ms = 0.0
                trace.ttfs_stop_point = "blocked_before_generate"
            trace_manager.complete_trace(fast_trace_id, status="blocked", error=sec_event.reason if sec_event else "blocked")
            raise ValueError(f"Security Alert: {sec_event.reason if sec_event else 'blocked'}")

        retrieval_start = time.time()
        evidences = knowledge_engine.retrieve(user_message, top_k=3)
        for ev in evidences:
            trace_manager.record_evidence(fast_trace_id, ev)
        retrieval_ms = (time.time() - retrieval_start) * 1000
        retrieval_confidence = sum(e.confidence for e in evidences) / len(evidences) if evidences else 0.0
        trace_manager.record_agent_call(
            fast_trace_id,
            AgentDecision(
                agent_name="Retriever",
                action="lightweight_retrieve",
                latency_ms=retrieval_ms,
                reasoning=f"items={len(evidences)}, retrieval_confidence={retrieval_confidence:.2f}",
            ),
        )

        context_builder = ContextBuilder()
        context_builder.add_layer("system", "You are a simulated customer in a sales training system.", priority=0, source="system")
        context_builder.add_layer("state", f"stage={self.fsm_state.current_stage.value}", priority=1, source="fsm")
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in self.conversation_history[-5:]])
        context_builder.add_layer("history", history_str, priority=2, source="memory")
        context_builder.add_layer("knowledge", knowledge_engine.format_for_prompt(evidences), priority=3, source="retriever")
        system_prompt = context_builder.build()
        trace_manager.set_context_usage(fast_trace_id, context_builder.get_usage())

        npc_start = time.time()
        budget_remaining = self.budget_manager.get_remaining_budget(self.session_id)
        routing_context = RoutingContext(
            agent_type=AgentType.NPC_GENERATOR,
            turn_importance=0.5,
            risk_level="high" if action == SecurityAction.DOWNGRADE else "low",
            budget_remaining=budget_remaining,
            latency_mode=LatencyMode.FAST,
            retrieval_confidence=retrieval_confidence,
            turn_number=turn_number,
            session_id=self.session_id,
            budget_authorized=True,
        )
        model_result = await self.model_gateway.chat(
            agent_type=AgentType.NPC_GENERATOR,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            context=routing_context,
            temperature=0.7,
        )
        npc_latency_ms = (time.time() - npc_start) * 1000

        npc_text = model_result.get("content", "")
        if retrieval_confidence < 0.6:
            npc_text = f"[no_evidence]{npc_text}"

        out_action, modified_text, out_event = runtime_guard.check_output(npc_text)
        if out_event:
            trace_manager.record_security_event(fast_trace_id, out_event)
        npc_text = modified_text

        trace_manager.record_agent_call(
            fast_trace_id,
            AgentDecision(
                agent_name="NPC",
                action="generate",
                provider=model_result.get("provider"),
                model_used=model_result.get("model"),
                latency_ms=model_result.get("latency_ms", npc_latency_ms),
                input_tokens=model_result.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=model_result.get("usage", {}).get("completion_tokens", 0),
                estimated_cost=model_result.get("cost_usd", 0.0),
                routing_reason=model_result.get("routing_reason"),
                downgrade_reason=model_result.get("downgrade_reason"),
                budget_remaining=model_result.get("budget_remaining"),
                reasoning="npc_returned" if retrieval_confidence >= 0.6 else "npc_returned (no_evidence)",
            ),
        )

        npc_reply = NpcReply(
            response=npc_text,
            mood_before=self.fsm_state.npc_mood,
            mood_after=self.fsm_state.npc_mood,
            mood_change_reason="v3 placeholder",
            expressed_signals=[],
            persona_consistency=0.8,
            stage_alignment=True,
        )

        evidence_pack = EvidencePack(
            items=[],
            retrieval_mode="lightweight",
            total_items=len(evidences),
            confidence=retrieval_confidence,
            retrieval_time_ms=retrieval_ms,
        )
        turn_plan = TurnPlan(
            turn_number=turn_number,
            path_mode="both",
            agents_to_call=["retriever", "npc_generator"],
            budget_allocation={},
            model_upgrade=False,
            risk_level="high" if action == SecurityAction.DOWNGRADE else "low",
            evidence_confidence=retrieval_confidence,
            reasoning="Fast path: retriever + npc only",
        )

        ttfs_ms = (time.time() - fast_start) * 1000
        trace = trace_manager.get_trace(fast_trace_id)
        if trace:
            trace.ttfs_ms = ttfs_ms
            trace.ttfs_stop_point = "npc_returned"
        trace_manager.complete_trace(fast_trace_id, status="success")

        self.metrics["fast_path_ttfs_ms"].append(ttfs_ms)
        logger.info("Fast Path completed: turn=%s, ttfs=%.0fms", turn_number, ttfs_ms)

        return FastPathResult(
            turn_number=turn_number,
            npc_reply=npc_reply,
            evidence_pack=evidence_pack,
            turn_plan=turn_plan,
            ttfs_ms=ttfs_ms,
            total_latency_ms=ttfs_ms,
        )

    async def _execute_slow_path_async(
        self,
        turn_number: int,
        user_message: str,
        npc_reply: NpcReply,
        slow_trace_id: str,
        fast_trace_id: str,
        db: Optional[AsyncSession] = None,
    ) -> SlowPathResult:
        result = await self._execute_slow_path(turn_number, user_message, npc_reply, slow_trace_id, db=db)
        trace_manager.link_slow_path(fast_trace_id, slow_trace_id, result.total_latency_ms)
        try:
            from app.api.endpoints.websocket import manager

            await manager.send_json(
                self.session_id,
                {
                    "type": "turn_analysis",
                    "turn": turn_number,
                    "coach_advice": result.coach_advice.model_dump() if result.coach_advice else None,
                    "evaluation": result.evaluation.model_dump() if result.evaluation else None,
                    "adoption_log": result.adoption_log.model_dump() if result.adoption_log else None,
                    "slow_path_latency_ms": result.total_latency_ms,
                },
            )
        except Exception as exc:
            logger.error("Failed to send slow path result: %s", exc)
        return result

    async def _execute_slow_path(
        self,
        turn_number: int,
        user_message: str,
        npc_reply: NpcReply,
        slow_trace_id: str,
        db: Optional[AsyncSession] = None,
    ) -> SlowPathResult:
        slow_start = time.time()
        try:
            budget_remaining = self.budget_manager.get_remaining_budget(self.session_id)
            routing_context = RoutingContext(
                agent_type=AgentType.COACH_GENERATOR,
                turn_importance=0.5,
                risk_level="low",
                budget_remaining=budget_remaining,
                latency_mode=LatencyMode.SLOW,
                retrieval_confidence=None,
                turn_number=turn_number,
                session_id=self.session_id,
                budget_authorized=True,
            )
            model_result = await self.model_gateway.chat(
                agent_type=AgentType.COACH_GENERATOR,
                messages=[
                    {"role": "system", "content": "You are a sales coach. Provide concise guidance."},
                    {"role": "user", "content": f"User: {user_message}\nNPC: {npc_reply.response}\nGive advice."},
                ],
                context=routing_context,
                temperature=0.3,
            )
            await asyncio.sleep(0.3)
            trace_manager.record_agent_call(
                slow_trace_id,
                AgentDecision(
                    agent_name="Coach",
                    action="generate",
                    provider=model_result.get("provider"),
                    model_used=model_result.get("model"),
                    latency_ms=model_result.get("latency_ms", (time.time() - slow_start) * 1000),
                    input_tokens=model_result.get("usage", {}).get("prompt_tokens", 0),
                    output_tokens=model_result.get("usage", {}).get("completion_tokens", 0),
                    estimated_cost=model_result.get("cost_usd", 0.0),
                    routing_reason=model_result.get("routing_reason"),
                    downgrade_reason=model_result.get("downgrade_reason"),
                    budget_remaining=model_result.get("budget_remaining"),
                ),
            )
            coach_advice = CoachAdvice(
                why="see trace",
                action="follow guidance",
                suggested_reply=model_result.get("content", ""),
                alternatives=[],
                guardrails=["cite evidence or state uncertainty for key claims"],
                priority="medium",
                confidence=0.6,
                technique_name=None,
            )
            total_latency_ms = (time.time() - slow_start) * 1000
            trace = trace_manager.get_trace(slow_trace_id)
            if trace:
                trace.total_latency_ms = total_latency_ms
            trace_manager.complete_trace(slow_trace_id, status="success")
            self.metrics["slow_path_total_ms"].append(total_latency_ms)
            logger.info("Slow Path completed: turn=%s, latency=%.0fms", turn_number, total_latency_ms)
            return SlowPathResult(
                turn_number=turn_number,
                coach_advice=coach_advice,
                evaluation=None,
                adoption_log=None,
                total_latency_ms=total_latency_ms,
            )
        except Exception as exc:
            logger.error("Slow Path error: %s", exc, exc_info=True)
            return SlowPathResult(
                turn_number=turn_number,
                total_latency_ms=(time.time() - slow_start) * 1000,
            )

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "fast_path_ttfs_ms": self.metrics["fast_path_ttfs_ms"],
            "slow_path_total_ms": self.metrics["slow_path_total_ms"],
            "provider_hits": self.model_gateway.get_stats()["call_stats"],
            "downgrade_count": self.metrics["downgrade_count"],
            "downgrade_reasons": self.metrics["downgrade_reasons"],
        }
