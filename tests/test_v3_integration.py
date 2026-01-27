"""
V3 integration tests: fast path, router hard rules, schema validation, budget manager.
"""
import asyncio

import pytest

from app.engine.coordinator.workflow_coordinator import SalesOrchestrator
from app.agents.coordination.session_director_v3 import SessionDirectorV3
from app.models.config_models import CustomerPersona
from app.schemas.fsm import FSMState, SalesStage
from app.infra.gateway.model_gateway import AgentType, BudgetManager, LatencyMode, ModelGateway, RoutingContext
from app.infra.gateway.model_gateway.router import ModelRouter


@pytest.fixture
def mock_persona():
    return CustomerPersona(
        id="test-persona",
        name="Test Customer",
        occupation="Manager",
        age_range="30-40",
        personality_traits=["cautious"],
        buying_motivation="efficiency",
        main_concerns="cost",
        communication_style="direct",
        decision_style="rational",
        initial_mood=0.5,
    )


@pytest.fixture
def v3_orchestrator(mock_persona):
    budget_manager = BudgetManager()
    model_gateway = ModelGateway(budget_manager=budget_manager)
    session_director = SessionDirectorV3(model_gateway, budget_manager)
    orchestrator = SalesOrchestrator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        session_director=session_director,
        persona=mock_persona,
    )
    fsm_state = FSMState(current_stage=SalesStage.OPENING, turn_count=0, npc_mood=0.5)
    orchestrator.initialize_session("test-session", "test-user", fsm_state)
    return orchestrator


@pytest.mark.asyncio
async def test_fast_path_not_blocked(v3_orchestrator):
    original_slow_path = v3_orchestrator._execute_slow_path

    async def mock_slow_path(*args, **kwargs):
        await asyncio.sleep(2.0)
        return await original_slow_path(*args, **kwargs)

    v3_orchestrator._execute_slow_path = mock_slow_path

    start_time = asyncio.get_event_loop().time()
    result = await v3_orchestrator.process_turn(turn_number=1, user_message="hello")
    elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    assert elapsed_ms < 3000, f"Fast Path took {elapsed_ms:.0f}ms, expected < 3000ms"
    assert result.fast_path_result.ttfs_ms < 3000
    assert result.fast_path_result.npc_reply is not None
    assert len(result.fast_path_result.npc_reply.response) > 0


@pytest.mark.asyncio
async def test_router_hard_rules():
    router = ModelRouter()

    context_hr1 = RoutingContext(
        agent_type=AgentType.COACH_GENERATOR,
        turn_importance=0.9,
        risk_level="low",
        budget_remaining=0.005,
        latency_mode=LatencyMode.SLOW,
        turn_number=1,
        session_id="test-session",
        budget_authorized=True,
    )
    decision_hr1 = router.route(context_hr1)
    assert "gpt-4" not in decision_hr1.model.lower() or decision_hr1.provider.value == "mock"
    assert "HR-1" in decision_hr1.reason or "BudgetCritical" in decision_hr1.reason

    context_hr2 = RoutingContext(
        agent_type=AgentType.NPC_GENERATOR,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=0.1,
        latency_mode=LatencyMode.FAST,
        turn_number=1,
        session_id="test-session",
        budget_authorized=True,
    )
    decision_hr2 = router.route(context_hr2)
    assert "gpt-4" not in decision_hr2.model.lower()
    assert decision_hr2.provider.value in ["qwen", "mock"]

    context_hr3 = RoutingContext(
        agent_type=AgentType.COACH_GENERATOR,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=0.1,
        latency_mode=LatencyMode.SLOW,
        retrieval_confidence=0.5,
        turn_number=1,
        session_id="test-session",
        budget_authorized=True,
    )
    decision_hr3 = router.route(context_hr3)
    assert "gpt-4" not in decision_hr3.model.lower()

    context_hr4_1 = RoutingContext(
        agent_type=AgentType.EVALUATOR,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=0.1,
        latency_mode=LatencyMode.SLOW,
        turn_number=1,
        session_id="test-session",
        budget_authorized=True,
    )
    decision_hr4_1 = router.route(context_hr4_1)
    model_1 = decision_hr4_1.model

    context_hr4_2 = RoutingContext(
        agent_type=AgentType.EVALUATOR,
        turn_importance=0.8,
        risk_level="high",
        budget_remaining=0.2,
        latency_mode=LatencyMode.SLOW,
        turn_number=2,
        session_id="test-session",
        budget_authorized=True,
    )
    decision_hr4_2 = router.route(context_hr4_2)
    model_2 = decision_hr4_2.model
    assert model_1 == model_2


@pytest.mark.asyncio
async def test_schema_validation():
    from app.schemas.v3_agent_outputs import CoachAdvice

    valid_advice = CoachAdvice(
        why="reason",
        action="action",
        suggested_reply="reply",
        alternatives=["alt1", "alt2"],
        guardrails=[],
        priority="medium",
        confidence=0.8,
    )
    assert valid_advice.model_dump() is not None

    with pytest.raises(Exception):
        CoachAdvice(why="test")  # missing required fields


@pytest.mark.asyncio
async def test_budget_manager():
    budget_manager = BudgetManager()
    session_id = "test-session"
    budget_manager.initialize_session(session_id)
    is_available, _ = budget_manager.check_budget(session_id, 0.02, "fast")
    assert is_available
    budget_manager.deduct_budget(session_id, 0.01, "fast")
    remaining = budget_manager.get_remaining_budget(session_id)
    assert remaining < 1.0
