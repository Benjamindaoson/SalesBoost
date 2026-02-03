"""
Production Coordinator - The Unified Facade

This is the ONLY entry point for all coordinator operations.
It routes to the appropriate backend engine based on configuration.

Design Principles:
1. Single Responsibility: Only route and delegate
2. Zero Business Logic: All logic is in backend coordinators
3. Configuration-Driven: Engine selection via config/feature flags
4. Backward Compatible: Supports all existing coordinators
5. Observable: All calls are traced and logged

Architecture:
    External Code → ProductionCoordinator (Facade) → Backend Engine
                                                    ↓
                                        ┌───────────┴───────────┐
                                        │                       │
                                  DynamicWorkflow      LangGraphCoordinator
                                  (Recommended)           (Legacy)

Usage:
    # In WebSocket handler or API endpoint
    from app.engine.coordinator.production_coordinator import get_production_coordinator

    coordinator = get_production_coordinator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        persona=persona,
        config=config
    )

    result = await coordinator.execute_turn(
        turn_number=1,
        user_message="你好",
        enable_async_coach=True
    )
"""

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from app.engine.coordinator.state import CoordinatorState, ExecutionMode, create_initial_state
from app.engine.coordinator.dynamic_workflow import (
    DynamicWorkflowCoordinator,
    get_full_config,
    WorkflowConfig
)
from app.schemas.fsm import FSMState, SalesStage
from core.config import get_settings
from app.config.feature_flags import FeatureFlags, CoordinatorEngine as FlagCoordinatorEngine

logger = logging.getLogger(__name__)


class CoordinatorEngine(str, Enum):
    """Available coordinator engines"""
    DYNAMIC_WORKFLOW = "dynamic_workflow"  # Recommended (configuration-driven)
    LANGGRAPH = "langgraph"  # Legacy (hard-coded graph)
    WORKFLOW = "workflow"  # Deprecated (wrapper around dynamic)


@dataclass
class TurnResult:
    """Standardized turn execution result"""
    turn_number: int
    npc_response: str
    npc_mood: float
    intent: str
    stage: str
    coach_advice: Optional[str] = None
    advice_source: Optional[str] = None  # NEW: Track advice source
    bandit_decision: Optional[dict] = None
    ttft_ms: float = 0.0
    trace: Optional[list] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


class ProductionCoordinator:
    """
    Production Coordinator - The Unified Facade

    This is the ONLY coordinator that external code should use.
    It automatically routes to the appropriate backend engine.

    Features:
    - Automatic engine selection based on config
    - Standardized interface (execute_turn)
    - TTFT optimization support (先答后评)
    - Graceful degradation (fallback advice)
    - Full observability (tracing, metrics)

    Example:
        coordinator = ProductionCoordinator(
            model_gateway=gateway,
            budget_manager=manager,
            persona=persona
        )

        # Synchronous mode (wait for coach)
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="这个产品多少钱?",
            enable_async_coach=False
        )

        # Asynchronous mode (TTFT optimization)
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="这个产品多少钱?",
            enable_async_coach=True  # Coach advice will be None
        )

        # Get coach advice later
        advice = await coordinator.get_coach_advice_async(
            turn_number=1,
            user_message="这个产品多少钱?",
            npc_response=result.npc_response
        )
    """

    def __init__(
        self,
        model_gateway: Any,
        budget_manager: Any,
        persona: Any,
        session_director: Any = None,
        config: Optional[WorkflowConfig] = None,
        engine: Optional[CoordinatorEngine] = None,
        max_history_len: int = 20,
        **kwargs
    ):
        """
        Initialize production coordinator

        Args:
            model_gateway: Model gateway for LLM calls
            budget_manager: Budget manager for cost control
            persona: Customer persona configuration
            session_director: Session director (optional, for legacy compatibility)
            config: Workflow configuration (optional, uses full config by default)
            engine: Coordinator engine to use (optional, auto-detected)
            max_history_len: Maximum conversation history length
            **kwargs: Additional arguments passed to backend coordinator
        """
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        self.persona = persona
        self.session_director = session_director
        self.max_history_len = max_history_len

        # Determine engine
        self.engine = self._determine_engine(engine)
        logger.info(f"[ProductionCoordinator] Using engine: {self.engine}")

        # Initialize backend coordinator
        self._backend = self._create_backend_coordinator(config)

        # State management
        self.fsm_state = FSMState(
            current_stage=SalesStage.OPENING,
            turn_count=0,
            npc_mood=0.5
        )
        self.session_id = "default"
        self.user_id = "default"
        self.history = []
        self.last_bandit_decision_id: Optional[str] = None

    def _determine_engine(self, engine: Optional[CoordinatorEngine]) -> CoordinatorEngine:
        """Determine which engine to use"""
        if engine:
            if engine == CoordinatorEngine.WORKFLOW and not get_settings().ALLOW_LEGACY_COORDINATOR:
                logger.warning(
                    "[ProductionCoordinator] Legacy WORKFLOW disabled; "
                    "falling back to DYNAMIC_WORKFLOW."
                )
                return CoordinatorEngine.DYNAMIC_WORKFLOW
            return engine

        # Check config/environment
        settings = get_settings()
        config_engine = getattr(settings, 'COORDINATOR_ENGINE', None)

        if config_engine:
            try:
                parsed = CoordinatorEngine(config_engine)
                if parsed == CoordinatorEngine.WORKFLOW and not settings.ALLOW_LEGACY_COORDINATOR:
                    logger.warning(
                        "[ProductionCoordinator] Legacy WORKFLOW disabled; "
                        "falling back to DYNAMIC_WORKFLOW."
                    )
                    return CoordinatorEngine.DYNAMIC_WORKFLOW
                return parsed
            except ValueError:
                logger.warning(
                    f"Invalid COORDINATOR_ENGINE: {config_engine}, "
                    f"falling back to DYNAMIC_WORKFLOW"
                )
        # Feature-flag fallback (legacy/workflow/langgraph)
        flag_engine = FeatureFlags.get_coordinator_engine()
        if flag_engine == FlagCoordinatorEngine.LANGGRAPH:
            return CoordinatorEngine.LANGGRAPH
        if flag_engine == FlagCoordinatorEngine.WORKFLOW:
            return CoordinatorEngine.DYNAMIC_WORKFLOW
        if flag_engine == FlagCoordinatorEngine.LEGACY:
            if not settings.ALLOW_LEGACY_COORDINATOR:
                logger.warning(
                    "[ProductionCoordinator] Legacy engine disabled; "
                    "falling back to DYNAMIC_WORKFLOW."
                )
                return CoordinatorEngine.DYNAMIC_WORKFLOW
            logger.warning(
                "[ProductionCoordinator] Legacy engine requested; "
                "using WORKFLOW wrapper for compatibility."
            )
            return CoordinatorEngine.WORKFLOW

        # Default to DYNAMIC_WORKFLOW (recommended)
        return CoordinatorEngine.DYNAMIC_WORKFLOW

    def _create_backend_coordinator(self, config: Optional[WorkflowConfig]) -> Any:
        """Create backend coordinator based on engine"""
        if self.engine == CoordinatorEngine.DYNAMIC_WORKFLOW:
            # Use DynamicWorkflowCoordinator (recommended)
            workflow_config = config or get_full_config()
            return DynamicWorkflowCoordinator(
                model_gateway=self.model_gateway,
                budget_manager=self.budget_manager,
                persona=self.persona,
                config=workflow_config
            )

        elif self.engine == CoordinatorEngine.LANGGRAPH:
            # Use LangGraphCoordinator (legacy)
            from app.engine.coordinator.langgraph_coordinator import LangGraphCoordinator
            return LangGraphCoordinator(
                model_gateway=self.model_gateway,
                budget_manager=self.budget_manager,
                persona=self.persona
            )

        elif self.engine == CoordinatorEngine.WORKFLOW:
            # Use WorkflowCoordinator (deprecated wrapper)
            from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
            if not get_settings().ALLOW_LEGACY_COORDINATOR:
                logger.warning(
                    "[ProductionCoordinator] Deprecated WorkflowCoordinator disabled; "
                    "falling back to DYNAMIC_WORKFLOW."
                )
                workflow_config = config or get_full_config()
                return DynamicWorkflowCoordinator(
                    model_gateway=self.model_gateway,
                    budget_manager=self.budget_manager,
                    persona=self.persona,
                    config=workflow_config,
                )
            logger.warning(
                "[ProductionCoordinator] Using deprecated WorkflowCoordinator. "
                "Please migrate to DYNAMIC_WORKFLOW."
            )
            return WorkflowCoordinator(
                model_gateway=self.model_gateway,
                budget_manager=self.budget_manager,
                session_director=self.session_director,
                persona=self.persona,
                max_history_len=self.max_history_len
            )

        else:
            raise ValueError(f"Unknown engine: {self.engine}")

    def initialize_session(
        self,
        session_id: str,
        user_id: str,
        state: Optional[FSMState] = None
    ) -> None:
        """
        Initialize session state

        Args:
            session_id: Session ID
            user_id: User ID
            state: Initial FSM state (optional)
        """
        self.session_id = session_id
        self.user_id = user_id

        if state is not None:
            self.fsm_state = state

        self.history = []

        # Initialize backend if needed
        if hasattr(self._backend, 'initialize_session'):
            self._backend.initialize_session(session_id, user_id, state)

        logger.info(
            f"[ProductionCoordinator] Session initialized: {session_id}, "
            f"user: {user_id}, engine: {self.engine}"
        )

    async def execute_turn(
        self,
        turn_number: int,
        user_message: str,
        enable_async_coach: bool = True
    ) -> TurnResult:
        """
        Execute one conversation turn

        This is the ONLY method external code should call.

        Args:
            turn_number: Current turn number
            user_message: User input message
            enable_async_coach: Enable TTFT optimization (default: True)

        Returns:
            TurnResult with NPC response and optional coach advice

        Raises:
            Exception: If execution fails
        """
        import time

        start_time = time.time()

        # Build state
        current_stage = getattr(self.fsm_state, "current_stage", None)
        if hasattr(current_stage, "value"):
            stage_value = current_stage.value
        elif current_stage is not None:
            stage_value = str(current_stage)
        else:
            stage_value = "unknown"
        fsm_state_dict = {
            "current_stage": stage_value,
            "turn_count": getattr(self.fsm_state, "turn_count", 0),
            "npc_mood": getattr(self.fsm_state, "npc_mood", 0.5),
        }

        try:

            # Delegate to backend
            if self.engine == CoordinatorEngine.DYNAMIC_WORKFLOW:
                result = await self._backend.execute_turn(
                    turn_number=turn_number,
                    user_message=user_message,
                    history=self.history,
                    fsm_state=fsm_state_dict,
                    session_id=self.session_id,
                    skip_coach=enable_async_coach  # TTFT optimization
                )

            elif self.engine == CoordinatorEngine.LANGGRAPH:
                result = await self._backend.execute_turn(
                    turn_number=turn_number,
                    user_message=user_message,
                    history=self.history,
                    fsm_state=fsm_state_dict,
                    session_id=self.session_id
                )

            elif self.engine == CoordinatorEngine.WORKFLOW:
                workflow_result = await self._backend.execute_turn(
                    turn_number=turn_number,
                    user_message=user_message,
                    enable_async_coach=enable_async_coach
                )
                # Convert WorkflowCoordinator result to standard format
                result = {
                    "npc_reply": workflow_result.npc_reply.response,
                    "npc_mood": workflow_result.npc_reply.mood_after,
                    "intent": workflow_result.intent,
                    "coach_advice": workflow_result.coach_advice,
                    "trace": workflow_result.trace,
                    "bandit_decision": workflow_result.bandit_decision,
                }

            # Update local state
            self._update_state(result, user_message)

            ttft_ms = (time.time() - start_time) * 1000

            # Construct standardized result
            tool_outputs = result.get("tool_outputs") or []
            cache_hit = any(output.get("cached") for output in tool_outputs)
            cache_key = None
            if cache_hit:
                cache_key = next(
                    (output.get("cache_key") for output in tool_outputs if output.get("cached")),
                    None,
                )
            return TurnResult(
                turn_number=turn_number,
                npc_response=result.get("npc_reply", ""),
                npc_mood=result.get("npc_mood", self.fsm_state.npc_mood),
                intent=result.get("intent", "unknown"),
                stage=stage_value,
                coach_advice=result.get("coach_advice"),
                advice_source=result.get("advice_source"),  # NEW: Track source
                bandit_decision=result.get("bandit_decision"),
                ttft_ms=ttft_ms,
                trace=result.get("trace"),
                metadata={
                    "cache_hit": cache_hit,
                    "cache_key": cache_key,
                },
                error=None
            )

        except Exception as e:
            logger.error(
                f"[ProductionCoordinator] Turn execution failed: {e}",
                exc_info=True
            )

            ttft_ms = (time.time() - start_time) * 1000

            return TurnResult(
                turn_number=turn_number,
                npc_response="",
                npc_mood=self.fsm_state.npc_mood,
                intent="error",
                stage=stage_value,
                coach_advice=None,
                ttft_ms=ttft_ms,
                trace=[],
                metadata={
                    "cache_hit": False,
                    "cache_key": None,
                },
                error=str(e)
            )

    async def record_bandit_feedback(
        self,
        decision_id: Optional[str],
        reward: float,
        signals: Optional[dict] = None,
    ) -> bool:
        if not decision_id:
            decision_id = self.last_bandit_decision_id
        if not decision_id:
            return False
        if hasattr(self._backend, "record_bandit_feedback"):
            ok = await self._backend.record_bandit_feedback(decision_id, reward, signals)
            if ok:
                logger.info("[Bandit] Reward updated for decision %s: %s", decision_id, reward)
            else:
                logger.warning("[Bandit] Reward update failed for decision %s", decision_id)
            return ok
        return False

    async def get_coach_advice_async(
        self,
        turn_number: int,
        user_message: str,
        npc_response: str
    ) -> Optional[Any]:
        """
        Generate coach advice asynchronously (for TTFT optimization)

        This method should be called in a background task after sending NPC response.

        Args:
            turn_number: Turn number
            user_message: User input
            npc_response: Generated NPC response

        Returns:
            Coach advice object or None if failed
        """
        try:
            # Delegate to backend if supported
            if hasattr(self._backend, 'get_coach_advice_async'):
                return await self._backend.get_coach_advice_async(
                    turn_number=turn_number,
                    user_message=user_message,
                    npc_response=npc_response
                )

            # Fallback: generate coach advice directly
            history_with_turn = self.history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": npc_response}
            ]

            if hasattr(self._backend, 'coach_agent'):
                advice = await self._backend.coach_agent.get_advice(
                    history=history_with_turn,
                    session_id=self.session_id,
                    turn_number=turn_number
                )

                logger.info(
                    f"[ProductionCoordinator] Async coach advice generated for "
                    f"session {self.session_id}, turn {turn_number}"
                )

                return advice

            logger.warning(
                "[ProductionCoordinator] Backend does not support async coach"
            )
            return None

        except Exception as e:
            logger.error(
                f"[ProductionCoordinator] Async coach advice failed: {e}",
                exc_info=True
            )
            return None

    def _update_state(self, result: Dict[str, Any], user_message: str):
        """Update local state based on execution result"""
        # Update mood
        if "npc_mood" in result:
            self.fsm_state.npc_mood = result["npc_mood"]

        # Update turn count
        self.fsm_state.turn_count += 1

        # Update history
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": result.get("npc_reply", "")})

        bandit_decision = result.get("bandit_decision") or {}
        decision_id = bandit_decision.get("decision_id")
        if decision_id:
            self.last_bandit_decision_id = decision_id

        # Prune history
        if len(self.history) > self.max_history_len * 2:
            self.history = self.history[-self.max_history_len * 2:]


# ==================== Factory Function ====================

def get_production_coordinator(
    model_gateway: Any,
    budget_manager: Any,
    persona: Any,
    session_director: Any = None,
    config: Optional[WorkflowConfig] = None,
    engine: Optional[CoordinatorEngine] = None,
    **kwargs
) -> ProductionCoordinator:
    """
    Factory function to create ProductionCoordinator

    This is the recommended way to create coordinators in production code.

    Args:
        model_gateway: Model gateway
        budget_manager: Budget manager
        persona: Customer persona
        session_director: Session director (optional)
        config: Workflow config (optional)
        engine: Engine override (optional)
        **kwargs: Additional arguments

    Returns:
        ProductionCoordinator instance

    Example:
        coordinator = get_production_coordinator(
            model_gateway=gateway,
            budget_manager=manager,
            persona=persona
        )
    """
    return ProductionCoordinator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        persona=persona,
        session_director=session_director,
        config=config,
        engine=engine,
        **kwargs
    )


_human_review_coordinator = None


def get_human_review_coordinator(
    model_gateway: Optional[Any] = None,
    budget_manager: Optional[Any] = None,
    persona: Optional[Any] = None,
    enable_checkpoints: bool = True,
):
    """
    Get or create the shared Human-in-the-Loop coordinator.

    This helper keeps API entrypoints from importing concrete coordinator classes.
    """
    global _human_review_coordinator
    if _human_review_coordinator is None:
        from app.engine.coordinator.human_in_loop_coordinator import HumanInLoopCoordinator
        from app.infra.gateway.model_gateway import ModelGateway

        gateway = model_gateway or ModelGateway()
        _human_review_coordinator = HumanInLoopCoordinator(
            model_gateway=gateway,
            budget_manager=budget_manager,
            persona=persona or {},
            enable_checkpoints=enable_checkpoints,
        )
    return _human_review_coordinator
