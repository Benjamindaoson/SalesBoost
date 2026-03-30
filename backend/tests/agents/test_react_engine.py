"""
Tests for ReAct Reasoning Engine
测试 ReAct 推理引擎的核心功能

覆盖:
- 推理循环完整性
- 提前终止条件
- 置信度计算
- 错误处理
- 性能基准
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from cognitive.skills.v3.react_reasoning_engine import (
    ReActReasoningEngine,
    ReActConfig,
    ReActResult,
    ReActStep,
    ThoughtOutput,
    ActionOutput,
    convert_react_to_turn_plan,
)
from schemas.fsm import FSMState, SalesStage


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_model_gateway():
    """Mock ModelGateway"""
    gateway = MagicMock()
    gateway.chat = AsyncMock(return_value={
        "content": """```json
{
    "situation_analysis": "客户对产品感兴趣，正在询问细节",
    "customer_signals": ["积极提问", "关注价格"],
    "key_challenges": ["预算限制"],
    "opportunities": ["可以介绍优惠"],
    "confidence": 0.8
}
```""",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    })
    return gateway


@pytest.fixture
def react_config():
    """ReAct 配置"""
    return ReActConfig(
        max_iterations=3,
        confidence_threshold=0.85,
        budget_per_step=0.005,
        enable_reflection=True,
    )


@pytest.fixture
def fsm_state():
    """FSM 状态"""
    return FSMState(
        current_stage=SalesStage.NEEDS_DISCOVERY,
        stage_history=[SalesStage.OPENING, SalesStage.NEEDS_DISCOVERY],
        slot_values={},
        stage_coverages={},
        turn_count=5,
        npc_mood=0.6,
        goal_achieved={},
    )


@pytest.fixture
def react_engine(mock_model_gateway, react_config):
    """ReAct 引擎实例"""
    return ReActReasoningEngine(
        model_gateway=mock_model_gateway,
        config=react_config,
    )


# ============================================================
# Test Cases: Basic Functionality
# ============================================================

class TestReActEngineBasic:
    """基础功能测试"""

    @pytest.mark.asyncio
    async def test_reason_returns_valid_result(self, react_engine, fsm_state):
        """测试推理返回有效结果"""
        result = await react_engine.reason(
            turn_number=5,
            fsm_state=fsm_state,
            user_message="这个产品的年费是多少?",
            conversation_history=[],
            session_id="test-session",
            user_id="test-user",
            budget_remaining=0.1,
        )

        assert isinstance(result, ReActResult)
        assert result.session_id == "test-session"
        assert result.turn_number == 5
        assert len(result.steps) > 0
        assert result.final_decision is not None

    @pytest.mark.asyncio
    async def test_reasoning_trace_is_captured(self, react_engine, fsm_state):
        """测试推理链路被记录"""
        result = await react_engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="你好",
            conversation_history=[],
            session_id="test-session",
            user_id="test-user",
            budget_remaining=0.1,
        )

        assert result.reasoning_trace is not None
        assert len(result.reasoning_trace) > 0
        assert "[Thought" in result.reasoning_trace

    @pytest.mark.asyncio
    async def test_step_structure_is_correct(self, react_engine, fsm_state):
        """测试步骤结构正确"""
        result = await react_engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试消息",
            conversation_history=[],
            session_id="test-session",
            user_id="test-user",
            budget_remaining=0.1,
        )

        for step in result.steps:
            assert isinstance(step, ReActStep)
            assert step.step_number > 0
            assert step.thought is not None
            assert step.action is not None
            assert step.latency_ms >= 0


# ============================================================
# Test Cases: Early Stopping
# ============================================================

class TestReActEarlyStopping:
    """提前终止测试"""

    @pytest.mark.asyncio
    async def test_stops_on_high_confidence(self, mock_model_gateway, fsm_state):
        """测试高置信度时提前终止"""
        # 模拟高置信度响应
        mock_model_gateway.chat = AsyncMock(return_value={
            "content": """```json
{
    "situation_analysis": "情况明确",
    "customer_signals": [],
    "key_challenges": [],
    "opportunities": [],
    "confidence": 0.95
}
```""",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        })

        config = ReActConfig(
            max_iterations=5,
            confidence_threshold=0.85,
        )
        engine = ReActReasoningEngine(mock_model_gateway, config)

        result = await engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.5,
        )

        assert result.early_stopped
        assert result.stop_reason == "confidence_reached"
        assert len(result.steps) < 5

    @pytest.mark.asyncio
    async def test_stops_on_budget_exhaustion(self, react_engine, fsm_state):
        """测试预算耗尽时终止"""
        result = await react_engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.001,  # 预算不足
        )

        assert result.early_stopped
        assert result.stop_reason == "budget_exhausted"


# ============================================================
# Test Cases: Action Selection
# ============================================================

class TestReActActionSelection:
    """行动选择测试"""

    @pytest.mark.asyncio
    async def test_action_type_based_on_stage(self, react_engine):
        """测试行动类型基于阶段"""
        # Closing 阶段
        closing_state = FSMState(
            current_stage=SalesStage.CLOSING,
            stage_history=[SalesStage.CLOSING],
            slot_values={},
            stage_coverages={},
            turn_count=10,
            npc_mood=0.7,
            goal_achieved={},
        )

        result = await react_engine.reason(
            turn_number=10,
            fsm_state=closing_state,
            user_message="好的，我考虑一下",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # Closing 阶段应该使用 both 路径
        assert result.final_decision.path_mode == "both"

    @pytest.mark.asyncio
    async def test_agents_to_call_includes_required(self, react_engine, fsm_state):
        """测试调用的 Agent 包含必需项"""
        result = await react_engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # 必须包含 retriever 和 npc_generator
        assert "retriever" in result.final_decision.agents_to_call
        assert "npc_generator" in result.final_decision.agents_to_call


# ============================================================
# Test Cases: Reflection Phase
# ============================================================

class TestReActReflection:
    """反思阶段测试"""

    @pytest.mark.asyncio
    async def test_reflection_affects_confidence(self, react_engine, fsm_state):
        """测试反思阶段影响置信度"""
        result = await react_engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试消息",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # 检查是否有反思步骤
        has_reflection = any(
            step.reflection is not None for step in result.steps
        )
        assert has_reflection or not react_engine.config.enable_reflection

    @pytest.mark.asyncio
    async def test_reflection_disabled(self, mock_model_gateway, fsm_state):
        """测试禁用反思"""
        config = ReActConfig(enable_reflection=False)
        engine = ReActReasoningEngine(mock_model_gateway, config)

        result = await engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # 没有反思步骤
        for step in result.steps:
            assert step.reflection is None


# ============================================================
# Test Cases: Backward Compatibility
# ============================================================

class TestReActBackwardCompatibility:
    """向后兼容性测试"""

    @pytest.mark.asyncio
    async def test_convert_to_turn_plan(self, react_engine, fsm_state):
        """测试转换为 TurnPlan 格式"""
        result = await react_engine.reason(
            turn_number=5,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        turn_plan = convert_react_to_turn_plan(result)

        assert "turn_number" in turn_plan
        assert "path_mode" in turn_plan
        assert "agents_to_call" in turn_plan
        assert "budget_allocation" in turn_plan
        assert "risk_level" in turn_plan
        assert "evidence_confidence" in turn_plan
        assert "reasoning" in turn_plan

        assert turn_plan["turn_number"] == 5


# ============================================================
# Test Cases: Performance
# ============================================================

class TestReActPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_latency_within_bounds(self, react_engine, fsm_state):
        """测试延迟在可接受范围内"""
        result = await react_engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # 总延迟应该在合理范围内 (mock 环境下应该很快)
        assert result.total_latency_ms < 5000  # 5 秒上限

        # 每步延迟应该被记录
        for step in result.steps:
            assert step.latency_ms >= 0


# ============================================================
# Test Cases: Error Handling
# ============================================================

class TestReActErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self, fsm_state):
        """测试优雅处理 LLM 失败"""
        gateway = MagicMock()
        gateway.chat = AsyncMock(side_effect=Exception("LLM Error"))

        engine = ReActReasoningEngine(gateway)

        result = await engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # 应该返回默认结果而不是崩溃
        assert result is not None
        assert result.final_decision is not None

    @pytest.mark.asyncio
    async def test_handles_invalid_json_response(self, fsm_state):
        """测试处理无效 JSON 响应"""
        gateway = MagicMock()
        gateway.chat = AsyncMock(return_value={
            "content": "这不是有效的 JSON",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        })

        engine = ReActReasoningEngine(gateway)

        result = await engine.reason(
            turn_number=1,
            fsm_state=fsm_state,
            user_message="测试",
            conversation_history=[],
            session_id="test",
            user_id="user",
            budget_remaining=0.1,
        )

        # 应该返回结果而不是崩溃
        assert result is not None


# ============================================================
# Test Cases: Data Models
# ============================================================

class TestReActDataModels:
    """数据模型测试"""

    def test_thought_output_validation(self):
        """测试 ThoughtOutput 验证"""
        thought = ThoughtOutput(
            situation_analysis="分析内容",
            customer_signals=["信号1"],
            key_challenges=["挑战1"],
            opportunities=["机会1"],
            confidence=0.8,
        )

        assert thought.confidence >= 0.0
        assert thought.confidence <= 1.0

    def test_action_output_validation(self):
        """测试 ActionOutput 验证"""
        action = ActionOutput(
            action_type="respond",
            priority="high",
            path_mode="both",
            agents_to_call=["retriever"],
            rationale="测试理由",
        )

        assert action.action_type in ["respond", "escalate", "defer", "clarify"]
        assert action.path_mode in ["fast", "slow", "both"]

    def test_react_result_serialization(self):
        """测试 ReActResult 序列化"""
        result = ReActResult(
            session_id="test",
            turn_number=1,
            steps=[],
            final_decision=ActionOutput(
                action_type="respond",
                path_mode="fast",
                rationale="测试",
            ),
            total_steps=0,
            total_latency_ms=100.0,
            final_confidence=0.8,
            reasoning_trace="测试链路",
        )

        # 应该能够转为字典
        data = result.model_dump()
        assert data["session_id"] == "test"
        assert data["turn_number"] == 1


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
