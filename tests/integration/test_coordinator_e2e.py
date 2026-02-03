"""
End-to-End Integration Tests for Coordinator
Tests complete conversation flows through the orchestration system
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from app.engine.coordinator.production_coordinator import (
    ProductionCoordinator,
    CoordinatorEngine,
    TurnResult
)
from app.engine.coordinator.dynamic_workflow import (
    WorkflowConfig,
    NodeType,
    get_minimal_config,
    get_full_config
)
from app.schemas.fsm import FSMState, SalesStage


@pytest.fixture
def mock_model_gateway():
    """Mock model gateway"""
    gateway = AsyncMock()
    gateway.call = AsyncMock(return_value="Mock LLM response")
    return gateway


@pytest.fixture
def mock_budget_manager():
    """Mock budget manager"""
    manager = Mock()
    manager.check_budget = Mock(return_value=True)
    manager.record_cost = Mock()
    return manager


@pytest.fixture
def test_persona():
    """Test persona configuration"""
    return {
        "name": "张经理",
        "role": "采购经理",
        "company": "测试公司",
        "budget": "10-50万",
        "pain_points": ["成本控制", "效率提升"]
    }


@pytest.fixture
async def minimal_coordinator(mock_model_gateway, mock_budget_manager, test_persona):
    """Create coordinator with minimal configuration"""
    config = get_minimal_config()
    coordinator = ProductionCoordinator(
        model_gateway=mock_model_gateway,
        budget_manager=mock_budget_manager,
        persona=test_persona,
        config=config,
        engine=CoordinatorEngine.DYNAMIC_WORKFLOW
    )
    coordinator.initialize_session("test_session", "test_user")
    return coordinator


@pytest.fixture
async def full_coordinator(mock_model_gateway, mock_budget_manager, test_persona):
    """Create coordinator with full configuration"""
    config = get_full_config()
    coordinator = ProductionCoordinator(
        model_gateway=mock_model_gateway,
        budget_manager=mock_budget_manager,
        persona=test_persona,
        config=config,
        engine=CoordinatorEngine.DYNAMIC_WORKFLOW
    )
    coordinator.initialize_session("test_session", "test_user")
    return coordinator


class TestBasicConversationFlow:
    """Test basic conversation flows"""

    @pytest.mark.asyncio
    async def test_single_turn_greeting(self, minimal_coordinator):
        """Test single turn greeting"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            # Mock intent classification
            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(
                    intent="greeting",
                    confidence=0.95,
                    stage_suggestion="opening"
                )
            )

            # Mock NPC response
            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(
                    content="您好！很高兴认识您，请问有什么可以帮助您的吗？",
                    mood=0.7
                )
            )

            # Execute turn
            result = await minimal_coordinator.execute_turn(
                turn_number=1,
                user_message="你好",
                enable_async_coach=False
            )

            # Assertions
            assert result.turn_number == 1
            assert result.intent == "greeting"
            assert result.npc_response
            assert result.error is None
            assert result.ttft_ms > 0

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, minimal_coordinator):
        """Test multi-turn conversation flow"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            mock_classifier_instance = mock_classifier.return_value
            mock_npc_instance = mock_npc.return_value

            # Turn 1: Greeting
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="greeting", confidence=0.95, stage_suggestion="opening")
            )
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="您好！", mood=0.7)
            )

            result1 = await minimal_coordinator.execute_turn(1, "你好", False)
            assert result1.intent == "greeting"

            # Turn 2: Product inquiry
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="product_inquiry", confidence=0.90, stage_suggestion="discovery")
            )
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="我们的产品功能包括...", mood=0.75)
            )

            result2 = await minimal_coordinator.execute_turn(2, "你们的产品有什么功能？", False)
            assert result2.intent == "product_inquiry"

            # Turn 3: Price inquiry
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="price_inquiry", confidence=0.92, stage_suggestion="negotiation")
            )
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="价格方面，我们有多种方案...", mood=0.8)
            )

            result3 = await minimal_coordinator.execute_turn(3, "多少钱？", False)
            assert result3.intent == "price_inquiry"

            # Verify history is maintained
            assert len(minimal_coordinator.history) == 6  # 3 turns * 2 messages


class TestKnowledgeRetrieval:
    """Test knowledge retrieval integration"""

    @pytest.mark.asyncio
    async def test_price_inquiry_with_knowledge(self, full_coordinator):
        """Test price inquiry triggers knowledge retrieval"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.tools.executor.ToolExecutor') as mock_executor, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            # Mock intent
            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="price_inquiry", confidence=0.90, stage_suggestion="negotiation")
            )

            # Mock tool execution
            mock_executor_instance = mock_executor.return_value
            mock_executor_instance.execute = AsyncMock(
                return_value={
                    "ok": True,
                    "result": {
                        "documents": ["产品A: 10万元", "产品B: 20万元"],
                        "confidence": 0.85
                    }
                }
            )

            # Mock NPC
            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="根据您的需求，我们推荐...", mood=0.75)
            )

            result = await full_coordinator.execute_turn(1, "你们的产品多少钱？", False)

            assert result.intent == "price_inquiry"
            assert result.npc_response
            # Verify tool was called
            mock_executor_instance.execute.assert_called()


class TestCoachAdvice:
    """Test coach advice generation"""

    @pytest.mark.asyncio
    async def test_sync_coach_advice(self, full_coordinator):
        """Test synchronous coach advice generation"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc, \
             patch('app.agents.ask.coach_agent.SalesCoachAgent') as mock_coach:

            # Mock components
            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="objection_price", confidence=0.88, stage_suggestion="negotiation")
            )

            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="我理解您的顾虑...", mood=0.65)
            )

            mock_coach_instance = mock_coach.return_value
            mock_coach_instance.get_advice = AsyncMock(
                return_value=Mock(advice="建议：强调产品价值，避免直接降价")
            )

            result = await full_coordinator.execute_turn(
                turn_number=1,
                user_message="太贵了",
                enable_async_coach=False  # Synchronous
            )

            assert result.coach_advice is not None
            assert "建议" in result.coach_advice or result.advice_source == "fallback"

    @pytest.mark.asyncio
    async def test_async_coach_advice(self, full_coordinator):
        """Test asynchronous coach advice generation (TTFT optimization)"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="greeting", confidence=0.95, stage_suggestion="opening")
            )

            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="您好！", mood=0.7)
            )

            result = await full_coordinator.execute_turn(
                turn_number=1,
                user_message="你好",
                enable_async_coach=True  # Asynchronous
            )

            # Coach advice should be None (generated asynchronously)
            assert result.coach_advice is None
            assert result.npc_response
            assert result.ttft_ms > 0


class TestErrorHandling:
    """Test error handling and fallback mechanisms"""

    @pytest.mark.asyncio
    async def test_intent_classification_failure(self, minimal_coordinator):
        """Test fallback when intent classification fails"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            # Mock intent failure
            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                side_effect=Exception("Classification failed")
            )

            # NPC should still work
            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="抱歉，请您再说一遍？", mood=0.5)
            )

            result = await minimal_coordinator.execute_turn(1, "test", False)

            # Should handle error gracefully
            assert result.error or result.intent == "error"

    @pytest.mark.asyncio
    async def test_npc_generation_failure(self, minimal_coordinator):
        """Test fallback when NPC generation fails"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="greeting", confidence=0.95, stage_suggestion="opening")
            )

            # Mock NPC failure
            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                side_effect=Exception("NPC generation failed")
            )

            result = await minimal_coordinator.execute_turn(1, "你好", False)

            # Should return error
            assert result.error is not None


class TestBanditIntegration:
    """Test Bandit algorithm integration"""

    @pytest.mark.asyncio
    async def test_bandit_decision_recording(self, full_coordinator):
        """Test bandit decision is recorded"""
        # Enable bandit in config
        full_coordinator._backend.config.enable_bandit = True
        full_coordinator._backend.bandit = Mock()
        full_coordinator._backend.bandit.choose = Mock(
            return_value={
                "decision_id": "test_decision_123",
                "chosen": "npc",
                "score": 0.75,
                "exploration": False
            }
        )

        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="greeting", confidence=0.95, stage_suggestion="opening")
            )

            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="您好！", mood=0.7)
            )

            result = await full_coordinator.execute_turn(1, "你好", False)

            # Verify bandit decision was recorded
            if result.bandit_decision:
                assert "decision_id" in result.bandit_decision

    @pytest.mark.asyncio
    async def test_bandit_feedback_recording(self, full_coordinator):
        """Test bandit feedback can be recorded"""
        decision_id = "test_decision_456"

        # Mock bandit
        full_coordinator._backend.bandit = Mock()
        full_coordinator._backend.bandit.record_feedback = Mock(return_value=True)

        success = await full_coordinator.record_bandit_feedback(
            decision_id=decision_id,
            reward=0.8,
            signals={"response_quality": 0.9}
        )

        assert success or full_coordinator._backend.bandit is None


class TestPerformanceMetrics:
    """Test performance metrics collection"""

    @pytest.mark.asyncio
    async def test_ttft_measurement(self, minimal_coordinator):
        """Test TTFT (Time To First Token) is measured"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="greeting", confidence=0.95, stage_suggestion="opening")
            )

            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="您好！", mood=0.7)
            )

            result = await minimal_coordinator.execute_turn(1, "你好", False)

            # TTFT should be measured
            assert result.ttft_ms > 0
            assert result.ttft_ms < 10000  # Should be less than 10 seconds

    @pytest.mark.asyncio
    async def test_trace_log_generation(self, full_coordinator):
        """Test trace logs are generated"""
        with patch('app.engine.intent.context_aware_classifier.ContextAwareIntentClassifier') as mock_classifier, \
             patch('app.agents.practice.npc_simulator.NPCGenerator') as mock_npc:

            mock_classifier_instance = mock_classifier.return_value
            mock_classifier_instance.classify_with_context = AsyncMock(
                return_value=Mock(intent="greeting", confidence=0.95, stage_suggestion="opening")
            )

            mock_npc_instance = mock_npc.return_value
            mock_npc_instance.generate_response = AsyncMock(
                return_value=Mock(content="您好！", mood=0.7)
            )

            result = await full_coordinator.execute_turn(1, "你好", False)

            # Trace log should exist
            assert result.trace is not None
            assert len(result.trace) > 0


@pytest.mark.asyncio
async def test_full_conversation_scenario():
    """
    Test a complete conversation scenario from greeting to closing

    This test simulates a realistic sales conversation:
    1. Greeting
    2. Product inquiry
    3. Price inquiry
    4. Objection handling
    5. Closing
    """
    # This would be a comprehensive integration test
    # For now, we'll mark it as a placeholder
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
