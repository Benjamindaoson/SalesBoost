"""
Intent classification integration tests.

NOTE: WorkflowCoordinator was replaced by DynamicWorkflowCoordinator +
ProductionCoordinator.  These tests now use ProductionCoordinator as the
entry-point (matching real production usage) with fully mocked LLM deps.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.engine.coordinator.production_coordinator import (
    ProductionCoordinator,
    get_production_coordinator,
)
from app.engine.coordinator.dynamic_workflow import get_minimal_config


def _make_coordinator():
    """Build a ProductionCoordinator with entirely mocked external deps."""
    mock_gateway = MagicMock()
    mock_budget_manager = MagicMock()
    mock_persona = {"name": "张总", "industry": "零售"}

    coord = ProductionCoordinator(
        model_gateway=mock_gateway,
        budget_manager=mock_budget_manager,
        persona=mock_persona,
        config=get_minimal_config(),
    )
    return coord


class TestIntentIntegration:
    """Test intent classification integration in production workflow."""

    @pytest.fixture
    def coordinator(self):
        return _make_coordinator()

    @pytest.mark.asyncio
    async def test_execute_turn_returns_npc_reply(self, coordinator):
        """execute_turn should return a dict with npc_reply."""
        mock_result = {
            "npc_reply": "这是NPC的回复",
            "npc_mood": 0.6,
            "coach_advice": None,
            "intent": "price_objection",
            "trace": [],
            "bandit_decision": {},
            "tool_outputs": [],
            "tool_results": [],
        }
        coordinator._backend = MagicMock()
        coordinator._backend.execute_turn = AsyncMock(return_value=mock_result)

        result = await coordinator.execute_turn(
            turn_number=1,
            user_message="这个价格太贵了，能便宜点吗",
        )

        assert result.npc_reply is not None
        assert result.turn_number == 1

    @pytest.mark.asyncio
    async def test_execute_turn_increments_turn_counter(self, coordinator):
        """Successive calls should increment the turn counter."""
        mock_result = {
            "npc_reply": "回复",
            "npc_mood": 0.5,
            "coach_advice": None,
            "intent": "greeting",
            "trace": [],
            "bandit_decision": {},
            "tool_outputs": [],
            "tool_results": [],
        }
        coordinator._backend = MagicMock()
        coordinator._backend.execute_turn = AsyncMock(return_value=mock_result)

        result1 = await coordinator.execute_turn(1, "你好")
        result2 = await coordinator.execute_turn(2, "谢谢")

        assert result1.turn_number == 1
        assert result2.turn_number == 2

    @pytest.mark.asyncio
    async def test_execute_turn_populates_history(self, coordinator):
        """After a turn, history should grow by 2 (user + assistant)."""
        mock_result = {
            "npc_reply": "很好！",
            "npc_mood": 0.7,
            "coach_advice": None,
            "intent": "product_inquiry",
            "trace": [],
            "bandit_decision": {},
            "tool_outputs": [],
            "tool_results": [],
        }
        coordinator._backend = MagicMock()
        coordinator._backend.execute_turn = AsyncMock(return_value=mock_result)

        initial_len = len(coordinator.history)
        await coordinator.execute_turn(1, "产品有什么功能")

        assert len(coordinator.history) == initial_len + 2

    @pytest.mark.asyncio
    async def test_execute_turn_error_handling(self, coordinator):
        """If backend raises, execute_turn should return an error TurnResult."""
        coordinator._backend = MagicMock()
        coordinator._backend.execute_turn = AsyncMock(
            side_effect=RuntimeError("LLM unavailable")
        )

        result = await coordinator.execute_turn(1, "测试")
        assert result.error is not None or result.npc_reply is not None  # graceful

    @pytest.mark.asyncio
    async def test_history_window_limit(self, coordinator):
        """History should not grow beyond max_history_len."""
        coordinator.max_history_len = 6  # 3 turns max
        coordinator._backend = MagicMock()
        coordinator._backend.execute_turn = AsyncMock(return_value={
            "npc_reply": "回复",
            "npc_mood": 0.5,
            "coach_advice": None,
            "intent": "greeting",
            "trace": [],
            "bandit_decision": {},
            "tool_outputs": [],
            "tool_results": [],
        })

        for i in range(5):
            await coordinator.execute_turn(i + 1, f"消息{i}")

        assert len(coordinator.history) <= coordinator.max_history_len
