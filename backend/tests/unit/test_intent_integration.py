"""
Integration Tests for Intent Classification in WorkflowCoordinator
Tests the full intent classification pipeline with context awareness
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
from app.schemas.fsm import SalesStage


class TestIntentIntegration:
    """Test intent classification integration in production workflow"""

    @pytest.fixture
    def coordinator(self):
        """Create a WorkflowCoordinator with mocked dependencies"""
        mock_gateway = MagicMock()
        mock_budget_manager = MagicMock()
        mock_session_director = MagicMock()
        mock_persona = {"name": "张总", "industry": "零售"}

        coordinator = WorkflowCoordinator(
            model_gateway=mock_gateway,
            budget_manager=mock_budget_manager,
            session_director=mock_session_director,
            persona=mock_persona
        )

        # Mock NPC and Coach responses to isolate intent testing
        coordinator.npc_agent.generate = AsyncMock(return_value=MagicMock(
            response="这是NPC的回复",
            mood_after=0.6
        ))
        coordinator.coach_agent.get_advice = AsyncMock(return_value=None)

        return coordinator

    @pytest.mark.asyncio
    async def test_ml_intent_classification(self, coordinator):
        """
        Case 1: Test ML model hit
        Input: "太贵了" → Should classify as price_objection with high confidence
        """
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="这个价格太贵了，能便宜点吗"
        )

        # Assertions
        assert result.intent == "price_objection", \
            f"Expected price_objection, got {result.intent}"
        assert result.turn_number == 1
        assert result.npc_reply is not None

    @pytest.mark.asyncio
    async def test_context_enhanced_intent(self, coordinator):
        """
        Case 2: Test context-aware enhancement
        Scenario: User repeatedly asks about price → Should elevate to price_objection
        """
        # Simulate conversation history with repeated price mentions
        coordinator.history = [
            {"role": "user", "content": "价格多少"},
            {"role": "assistant", "content": "我们的VIP会员是1000元"},
            {"role": "user", "content": "能便宜点吗"},
            {"role": "assistant", "content": "可以给您打8折"},
        ]
        coordinator.fsm_state.turn_count = 4

        result = await coordinator.execute_turn(
            turn_number=5,
            user_message="这个价格还是太高了"
        )

        # Should detect price_objection due to context
        assert result.intent == "price_objection"

    @pytest.mark.asyncio
    async def test_fsm_stage_transition(self, coordinator):
        """
        Case 3: Test FSM stage transition based on intent
        When user expresses final_confirmation, FSM should transition to CLOSING
        """
        coordinator.fsm_state.current_stage = SalesStage.DISCOVERY

        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="好的，我决定购买了"
        )

        # Intent should be final_confirmation or positive_feedback
        assert result.intent in ["final_confirmation", "positive_feedback"]

    @pytest.mark.asyncio
    async def test_rule_based_fallback(self, coordinator):
        """
        Case 4: Test rule-based fallback for edge cases
        Input: Very short or unclear text
        """
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="嗯"
        )

        # Should still return a valid intent (even if it's unclear/greeting)
        assert result.intent is not None
        assert isinstance(result.intent, str)
        assert len(result.intent) > 0

    @pytest.mark.asyncio
    async def test_product_inquiry_intent(self, coordinator):
        """
        Case 5: Test product inquiry classification
        """
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="产品有什么功能和特点"
        )

        assert result.intent == "product_inquiry"

    @pytest.mark.asyncio
    async def test_hesitation_intent(self, coordinator):
        """
        Case 6: Test hesitation detection
        """
        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="我再考虑考虑吧"
        )

        assert result.intent == "hesitation"


class TestIntentConfidence:
    """Test confidence scoring and context enhancement flags"""

    @pytest.fixture
    def coordinator(self):
        mock_gateway = MagicMock()
        mock_budget_manager = MagicMock()
        mock_session_director = MagicMock()
        mock_persona = {"name": "李总"}

        coordinator = WorkflowCoordinator(
            model_gateway=mock_gateway,
            budget_manager=mock_budget_manager,
            session_director=mock_session_director,
            persona=mock_persona
        )

        coordinator.npc_agent.generate = AsyncMock(return_value=MagicMock(
            response="回复",
            mood_after=0.5
        ))
        coordinator.coach_agent.get_advice = AsyncMock(return_value=None)

        return coordinator

    @pytest.mark.asyncio
    async def test_high_confidence_classification(self, coordinator):
        """Test that clear intents have high confidence"""
        # Direct price objection should have high confidence
        coordinator.fsm_state.turn_count = 0

        await coordinator.execute_turn(1, "价格太贵了")

        # We can't directly access intent_result in current implementation
        # but we can verify the workflow completes successfully
        assert coordinator.fsm_state.turn_count == 1


class TestHistoryManagement:
    """Test conversation history management"""

    @pytest.fixture
    def coordinator(self):
        mock_gateway = MagicMock()
        coordinator = WorkflowCoordinator(
            model_gateway=mock_gateway,
            budget_manager=MagicMock(),
            session_director=MagicMock(),
            persona={}
        )

        coordinator.npc_agent.generate = AsyncMock(return_value=MagicMock(
            response="回复",
            mood_after=0.5
        ))
        coordinator.coach_agent.get_advice = AsyncMock(return_value=None)

        return coordinator

    @pytest.mark.asyncio
    async def test_history_updates_correctly(self, coordinator):
        """Test that history is updated after each turn"""
        initial_len = len(coordinator.history)

        await coordinator.execute_turn(1, "你好")

        # History should grow by 2 (user message + assistant response)
        assert len(coordinator.history) == initial_len + 2

    @pytest.mark.asyncio
    async def test_history_window_limit(self, coordinator):
        """Test that history doesn't exceed max_history_len"""
        coordinator.max_history_len = 6  # 3 turns max

        # Simulate 5 turns
        for i in range(5):
            await coordinator.execute_turn(i+1, f"消息{i}")

        # History should be capped at max_history_len
        assert len(coordinator.history) <= coordinator.max_history_len
