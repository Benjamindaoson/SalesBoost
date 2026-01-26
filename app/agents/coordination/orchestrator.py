"""
Session Orchestrator - V2 compatibility wrapper with V3 budget enforcement.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.roles.coach_agent import CoachAgent
from app.agents.roles.compliance_agent import ComplianceAgent
from app.agents.roles.evaluator_agent import EvaluatorAgent
from app.agents.roles.intent_gate import IntentGateAgent
from app.agents.roles.npc_agent import NPCAgent
from app.agents.roles.rag_agent import RAGAgent
from app.core.llm_context import LLMCallContext
from app.fsm.engine import FSMEngine
from app.models.config_models import CustomerPersona, ScenarioConfig
from app.schemas.agent_outputs import OrchestratorTurnResult
from app.schemas.fsm import FSMState, SalesStage
from app.schemas.trace import CallType
from app.security.runtime_guard import SecurityAction, runtime_guard
from app.services.adoption_tracker import AdoptionTracker
from app.services.context_engine import ContextBuilder
from app.services.curriculum_planner import CurriculumPlanner
from app.services.knowledge_engine import knowledge_engine
from app.services.model_gateway import model_gateway
from app.services.observability import trace_manager
from app.services.state_updater import StateUpdater
from app.services.strategy_analyzer import StrategyAnalyzer

logger = logging.getLogger(__name__)


class NullReflectionAgent:
    async def reflect_and_store(self, *args: Any, **kwargs: Any) -> None:
        return None


class SessionOrchestrator:
    """V2-style orchestrator with standardized execute_turn API."""

    def __init__(
        self,
        scenario_config: ScenarioConfig,
        customer_persona: CustomerPersona,
        fsm_engine: Optional[FSMEngine] = None,
    ) -> None:
        self.scenario_config = scenario_config
        self.customer_persona = customer_persona
        self.fsm_engine = fsm_engine or FSMEngine()

        self.intent_gate = IntentGateAgent()
        self.npc_agent = NPCAgent(persona=customer_persona)
        self.coach_agent = CoachAgent()
        self.evaluator_agent = EvaluatorAgent()
        self.rag_agent = RAGAgent()
        self.compliance_agent = ComplianceAgent()

        self.state_updater = StateUpdater(fsm_engine=self.fsm_engine)
        self.adoption_tracker = AdoptionTracker()
        self.strategy_analyzer = StrategyAnalyzer()
        self.curriculum_planner = CurriculumPlanner()

        try:
            from app.agents.v3.reflection_agent import ReflectionAgent

            self.reflection_agent = ReflectionAgent()
        except Exception:
            self.reflection_agent = NullReflectionAgent()

        self.fsm_state: Optional[FSMState] = None
        self.conversation_history: list[Dict[str, Any]] = []
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None

        self.model_gateway = model_gateway
        self.budget_manager = model_gateway.budget_manager

    async def initialize_session(self, session_id: str, user_id: str) -> FSMState:
        self.session_id = session_id
        self.user_id = user_id
        self.fsm_state = self.fsm_engine.create_initial_state()
        self.conversation_history = []
        self.budget_manager.initialize_session(session_id)
        logger.info("Session initialized: %s, user=%s", session_id, user_id)
        return self.fsm_state

    async def execute_turn(
        self,
        user_message: str,
        session: Any,
        db: AsyncSession,
    ) -> OrchestratorTurnResult:
        if not self.fsm_state:
            raise RuntimeError("Session not initialized")
        if not self.budget_manager.is_authorized(self.session_id):
            raise RuntimeError(f"Budget not authorized for session: {self.session_id}")

        turn_start = datetime.utcnow()
        current_turn = self.fsm_state.turn_count + 1
        trace_id = trace_manager.start_trace(self.session_id, current_turn, CallType.FAST_PATH)

        action, sec_event = runtime_guard.check_input(user_message)
        if sec_event:
            trace_manager.record_security_event(trace_id, sec_event)
        if action == SecurityAction.BLOCK:
            raise ValueError(f"Security Alert: {sec_event.reason if sec_event else 'blocked'}")

        self.conversation_history.append(
            {
                "role": "user",
                "content": user_message,
                "turn": current_turn,
                "timestamp": turn_start.isoformat(),
            }
        )

        context_builder = ContextBuilder()
        context_builder.add_layer("system", "You are a simulated customer in a sales training system.", priority=0)
        context_builder.add_layer("state", f"stage={self.fsm_state.current_stage.value}", priority=1)
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in self.conversation_history[-5:]])
        context_builder.add_layer("history", history_str, priority=2)
        evidences = knowledge_engine.retrieve(user_message)
        for ev in evidences:
            trace_manager.record_evidence(trace_id, ev)
        context_builder.add_layer("knowledge", knowledge_engine.format_for_prompt(evidences), priority=3)
        trace_manager.set_context_usage(trace_id, context_builder.get_usage())

        llm_context_fast = self._build_llm_context(current_turn, "fast", trace_id)

        intent_result = await self.intent_gate.analyze(
            user_message=user_message,
            current_stage=self.fsm_state.current_stage,
            conversation_history=self.conversation_history,
            stage_config=self.fsm_engine.get_stage_config(self.fsm_state.current_stage),
            llm_context=llm_context_fast,
        )
        rag_result, compliance_result = await asyncio.gather(
            self.rag_agent.retrieve(
                query=user_message,
                stage=self.fsm_state.current_stage,
                context={"full_context": context_builder.build()},
            ),
            self.compliance_agent.check(
                message=user_message,
                stage=self.fsm_state.current_stage,
                llm_context=llm_context_fast,
            ),
        )
        npc_result = await self.npc_agent.generate_response(
            user_message=user_message,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            intent_result=intent_result,
            llm_context=llm_context_fast,
        )

        out_action, modified_text, out_event = runtime_guard.check_output(npc_result.response)
        if out_event:
            trace_manager.record_security_event(trace_id, out_event)
            npc_result.response = modified_text

        self.conversation_history.append(
            {
                "role": "npc",
                "content": npc_result.response,
                "turn": current_turn,
                "timestamp": datetime.utcnow().isoformat(),
                "mood": npc_result.mood_after,
            }
        )

        processing_time_ms = (datetime.utcnow() - turn_start).total_seconds() * 1000
        trace = trace_manager.get_trace(trace_id)
        if trace:
            trace.ttfs_ms = processing_time_ms
        trace_manager.complete_trace(trace_id, status="success")

        return await self._process_analysis(
            turn_number=current_turn,
            user_message=user_message,
            intent_result=intent_result,
            rag_result=rag_result,
            compliance_result=compliance_result,
            npc_result=npc_result,
            processing_time_ms=processing_time_ms,
            timestamp=turn_start.isoformat(),
            db=db,
        )

    async def process_turn(self, user_message: str, session: Any, db: AsyncSession) -> OrchestratorTurnResult:
        return await self.execute_turn(user_message=user_message, session=session, db=db)

    async def _process_analysis(
        self,
        turn_number: int,
        user_message: str,
        intent_result: Any,
        rag_result: Any,
        compliance_result: Any,
        npc_result: Any,
        processing_time_ms: float,
        timestamp: str,
        db: AsyncSession,
    ) -> OrchestratorTurnResult:
        current_turn = turn_number
        llm_context_slow = self._build_llm_context(current_turn, "slow", None)

        coach_result, _ = await self.coach_agent.generate_advice(
            user_message=user_message,
            npc_response=npc_result.response,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            rag_content=rag_result,
            compliance_result=compliance_result,
            strategy_analysis=None,
            llm_context=llm_context_slow,
        )
        evaluator_result, _ = await self.evaluator_agent.evaluate(
            user_message=user_message,
            npc_response=npc_result.response,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            stage_config=self.fsm_engine.get_stage_config(self.fsm_state.current_stage),
            compliance_result=compliance_result,
            llm_context=llm_context_slow,
        )

        adoption_analysis = await self.adoption_tracker.analyze_adoption(
            session_id=self.session_id,
            user_id=self.user_id,
            current_turn=current_turn,
            user_message=turn_result.user_message,
            current_scores=evaluator_result.dimension_scores,
            db=db,
        )
        prev_npc_message = ""
        for msg in reversed(self.conversation_history[:-1]):
            if msg.get("role") == "npc":
                prev_npc_message = msg.get("content", "")
                break
        strategy_analysis_result = self.strategy_analyzer.analyze_strategy(
            user_message=user_message,
            npc_message=prev_npc_message,
            stage=self.fsm_state.current_stage,
        )
        mood_change = npc_result.mood_after - npc_result.mood_before
        await self.strategy_analyzer.save_strategy_decision(
            db=db,
            session_id=self.session_id,
            user_id=self.user_id,
            turn_id=current_turn,
            analysis=strategy_analysis_result,
            npc_mood_change=mood_change,
            goal_progress=evaluator_result.goal_advanced,
            immediate_score=evaluator_result.overall_score,
        )

        self.fsm_state, transition_decision = await self.state_updater.update(
            state=self.fsm_state,
            intent_result=turn_result.intent_result,
            npc_result=turn_result.npc_result,
            evaluator_result=evaluator_result,
            current_turn=current_turn,
        )
        self.fsm_state = self.fsm_engine.increment_turn(self.fsm_state)

        turn_result = OrchestratorTurnResult(
            turn_number=current_turn,
            user_message=user_message,
            intent_result=intent_result,
            rag_result=rag_result,
            compliance_result=compliance_result,
            npc_result=npc_result,
            coach_result=coach_result,
            evaluator_result=evaluator_result,
            strategy_analysis=strategy_analysis_result.model_dump() if strategy_analysis_result else None,
            adoption_analysis=adoption_analysis.model_dump() if adoption_analysis else None,
            transition_decision=transition_decision,
            fsm_state_snapshot=self.fsm_state.model_copy(deep=True),
            processing_time_ms=processing_time_ms,
            timestamp=timestamp,
        )

        if self.fsm_state.current_stage in [SalesStage.OBJECTION_HANDLING, SalesStage.CLOSING]:
            try:
                await self.reflection_agent.reflect_and_store(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    conversation_history=self.conversation_history,
                )
            except Exception as exc:
                logger.warning("Reflection failed: %s", exc)

        return turn_result

    def is_session_completed(self) -> bool:
        if not self.fsm_state:
            return False
        return self.fsm_state.current_stage == SalesStage.COMPLETED

    async def complete_session(self, db: AsyncSession) -> Optional[Dict[str, Any]]:
        if not self.user_id:
            logger.warning("Cannot complete session: user_id not set")
            return None
        try:
            curriculum_plan = await self.curriculum_planner.generate_curriculum(
                db=db,
                user_id=self.user_id,
                max_focus_items=3,
            )
            profile = await StrategyAnalyzer.get_user_strategy_profile(db, self.user_id)
            recommended_focus = None
            if curriculum_plan.next_training_plan:
                first_focus = curriculum_plan.next_training_plan[0]
                recommended_focus = {
                    "stage": first_focus.stage,
                    "situation": first_focus.focus_situation,
                    "strategy": first_focus.focus_strategy,
                    "difficulty": first_focus.difficulty,
                }
            return {
                "user_id": self.user_id,
                "next_training_focus": recommended_focus,
                "overall_improvement": profile.get("effective_adoption_rate", 0.0) if profile else 0.0,
                "curriculum_reasoning": curriculum_plan.reasoning,
                "expected_improvement": curriculum_plan.expected_improvement,
            }
        except Exception as exc:
            logger.error("Error completing session: %s", exc, exc_info=True)
            return None

    def dispose(self) -> None:
        self.conversation_history.clear()
        self.fsm_state = None
        logger.info("Orchestrator disposed for session %s", self.session_id)

    def _build_llm_context(self, turn_number: int, latency_mode: str, trace_id: Optional[str]) -> LLMCallContext:
        return LLMCallContext(
            session_id=self.session_id or "unknown",
            turn_number=turn_number,
            latency_mode=latency_mode,
            turn_importance=0.5,
            risk_level="low",
            budget_remaining=self.budget_manager.get_remaining_budget(self.session_id or "unknown"),
            retrieval_confidence=None,
            trace_id=trace_id,
            budget_authorized=True,
        )
