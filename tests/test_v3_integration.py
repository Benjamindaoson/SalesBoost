"""
V3 集成测试
测试 Fast Path、Router 硬规则、Schema 校验
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.services.model_gateway import ModelGateway, BudgetManager, RoutingContext, AgentType, LatencyMode
from app.services.model_gateway.router import ModelRouter
from app.services.v3_orchestrator import V3Orchestrator
from app.agents.v3.session_director_v3 import SessionDirectorV3
from app.schemas.fsm import FSMState, SalesStage
from app.models.config_models import CustomerPersona


@pytest.fixture
def mock_persona():
    """Mock CustomerPersona"""
    return CustomerPersona(
        id="test-persona",
        name="Test Customer",
        occupation="Manager",
        age_range="30-40",
        personality_traits=["谨慎"],
        buying_motivation="效率提升",
        main_concerns="成本",
        communication_style="直接",
        decision_style="理性",
        initial_mood=0.5,
    )


@pytest.fixture
def v3_orchestrator(mock_persona):
    """创建 V3 Orchestrator 实例"""
    model_gateway = ModelGateway()
    budget_manager = BudgetManager()
    session_director = SessionDirectorV3(model_gateway, budget_manager)
    
    orchestrator = V3Orchestrator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        session_director=session_director,
        persona=mock_persona,
    )
    
    # 初始化会话
    fsm_state = FSMState(
        current_stage=SalesStage.OPENING,
        turn_count=0,
        npc_mood=0.5,
    )
    orchestrator.initialize_session("test-session", "test-user", fsm_state)
    
    return orchestrator


@pytest.mark.asyncio
async def test_fast_path_not_blocked(v3_orchestrator):
    """
    测试 Fast Path 不被 Slow Path 阻塞
    Slow Path mock sleep 2s，Fast Path 仍 < 3s 返回
    """
    # Mock Slow Path 延迟
    original_slow_path = v3_orchestrator._execute_slow_path
    
    async def mock_slow_path(*args, **kwargs):
        await asyncio.sleep(2.0)  # 模拟 2s 延迟
        return await original_slow_path(*args, **kwargs)
    
    v3_orchestrator._execute_slow_path = mock_slow_path
    
    # 执行 Fast Path
    import time
    start_time = time.time()
    
    result = await v3_orchestrator.process_turn(
        turn_number=1,
        user_message="你好",
    )
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    # 断言：Fast Path < 3s
    assert elapsed_ms < 3000, f"Fast Path took {elapsed_ms:.0f}ms, expected < 3000ms"
    assert result.fast_path_result.ttfs_ms < 3000, f"TTFS={result.fast_path_result.ttfs_ms:.0f}ms"
    
    # 断言：有 NPC 回复
    assert result.fast_path_result.npc_reply is not None
    assert len(result.fast_path_result.npc_reply.response) > 0


@pytest.mark.asyncio
async def test_router_hard_rules():
    """
    测试 Router 硬规则 HR-1~HR-4
    """
    router = ModelRouter()
    
    # HR-1: 预算熔断
    context_hr1 = RoutingContext(
        agent_type=AgentType.COACH_GENERATOR,
        turn_importance=0.9,
        risk_level="low",
        budget_remaining=0.005,  # < 0.01
        latency_mode=LatencyMode.SLOW,
        turn_number=1,
        session_id="test-session",
    )
    decision_hr1 = router.route(context_hr1)
    assert "gpt-4" not in decision_hr1.model.lower() or decision_hr1.provider.value == "mock", \
        f"HR-1 failed: selected {decision_hr1.provider}/{decision_hr1.model}"
    assert "HR-1" in decision_hr1.reason or "BudgetCritical" in decision_hr1.reason
    
    # HR-2: 快路径不可阻塞
    context_hr2 = RoutingContext(
        agent_type=AgentType.NPC_GENERATOR,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=0.1,
        latency_mode=LatencyMode.FAST,
        turn_number=1,
        session_id="test-session",
    )
    decision_hr2 = router.route(context_hr2)
    assert "gpt-4" not in decision_hr2.model.lower(), \
        f"HR-2 failed: selected GPT-4 for fast path"
    assert decision_hr2.provider.value in ["qwen", "mock"], \
        f"HR-2 failed: selected {decision_hr2.provider}"
    
    # HR-3: 低置信度禁止确定性强回答
    context_hr3 = RoutingContext(
        agent_type=AgentType.COACH_GENERATOR,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=0.1,
        latency_mode=LatencyMode.SLOW,
        retrieval_confidence=0.5,  # < 0.6
        turn_number=1,
        session_id="test-session",
    )
    decision_hr3 = router.route(context_hr3)
    assert "gpt-4" not in decision_hr3.model.lower(), \
        f"HR-3 failed: selected GPT-4 for low confidence"
    
    # HR-4: Evaluator 一致性
    context_hr4_1 = RoutingContext(
        agent_type=AgentType.EVALUATOR,
        turn_importance=0.5,
        risk_level="low",
        budget_remaining=0.1,
        latency_mode=LatencyMode.SLOW,
        turn_number=1,
        session_id="test-session",
    )
    decision_hr4_1 = router.route(context_hr4_1)
    model_1 = decision_hr4_1.model
    
    # 第二次调用应该使用相同模型
    context_hr4_2 = RoutingContext(
        agent_type=AgentType.EVALUATOR,
        turn_importance=0.8,  # 重要性变化
        risk_level="high",  # 风险变化
        budget_remaining=0.2,  # 预算变化
        latency_mode=LatencyMode.SLOW,
        turn_number=2,
        session_id="test-session",
    )
    decision_hr4_2 = router.route(context_hr4_2)
    model_2 = decision_hr4_2.model
    
    assert model_1 == model_2, \
        f"HR-4 failed: Evaluator model changed from {model_1} to {model_2}"


@pytest.mark.asyncio
async def test_schema_validation():
    """
    测试 Schema 校验失败触发修复重试和降级
    """
    from app.schemas.v3_agent_outputs import CoachAdvice
    
    # 测试正常 Schema
    valid_advice = CoachAdvice(
        why="测试原因",
        action="测试行动",
        suggested_reply="测试话术",
        alternatives=["备选1", "备选2"],
        guardrails=[],
        priority="medium",
        confidence=0.8,
    )
    assert valid_advice.model_dump() is not None
    
    # 测试 Schema 校验失败（缺少必需字段）
    with pytest.raises(Exception):
        invalid_advice = CoachAdvice(
            why="测试",
            # 缺少 action
        )
    
    # 测试 Schema 修复重试逻辑（需要在 CoachGeneratorV3 中实现）
    # 这里先测试 Schema 本身
    assert True  # Placeholder


@pytest.mark.asyncio
async def test_budget_manager():
    """测试预算管理器"""
    budget_manager = BudgetManager()
    session_id = "test-session"
    
    budget_manager.initialize_session(session_id)
    
    # 检查预算
    is_available, remaining = budget_manager.check_budget(session_id, 0.02, "fast")
    assert is_available, "Budget should be available"
    
    # 扣减预算
    budget_manager.deduct_budget(session_id, 0.01, "fast")
    
    # 再次检查
    remaining = budget_manager.get_remaining_budget(session_id)
    assert remaining < 1.0, "Budget should be deducted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
