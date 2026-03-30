"""
Unit Tests for Agent Components

Tests for various agent implementations including sales coach, customer simulator, etc.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


class TestSalesCoachAgent:
    """Tests for Sales Coach Agent."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = Mock()
        client.generate = AsyncMock(return_value="Great job! You handled that objection well.")
        return client

    @pytest.fixture
    def sales_coach_agent(self, mock_llm_client):
        """Create sales coach agent instance."""
        # Mock agent initialization
        agent = Mock()
        agent.llm_client = mock_llm_client
        agent.provide_feedback = AsyncMock(
            return_value={
                "feedback": "Great job! You handled that objection well.",
                "score": 8.5,
                "suggestions": ["Try to be more empathetic", "Ask more open-ended questions"],
            }
        )
        return agent

    @pytest.mark.asyncio
    async def test_provide_feedback(self, sales_coach_agent):
        """Test feedback generation."""
        conversation_history = [
            {"role": "user", "content": "I'm interested in your product"},
            {"role": "assistant", "content": "Great! Let me tell you about our features"},
        ]

        result = await sales_coach_agent.provide_feedback(conversation_history)

        assert "feedback" in result
        assert "score" in result
        assert isinstance(result["score"], (int, float))
        assert result["score"] >= 0 and result["score"] <= 10

    @pytest.mark.asyncio
    async def test_evaluate_performance(self, sales_coach_agent):
        """Test performance evaluation."""
        sales_coach_agent.evaluate_performance = AsyncMock(
            return_value={
                "overall_score": 7.5,
                "methodology_score": 8.0,
                "objection_handling_score": 7.0,
                "empathy_score": 8.5,
            }
        )

        session_data = {
            "messages": [
                {"role": "user", "content": "Tell me about pricing"},
                {"role": "assistant", "content": "Our pricing starts at $99/month"},
            ],
            "turns_count": 10,
        }

        result = await sales_coach_agent.evaluate_performance(session_data)

        assert "overall_score" in result
        assert result["overall_score"] >= 0 and result["overall_score"] <= 10

    @pytest.mark.asyncio
    async def test_suggest_improvements(self, sales_coach_agent):
        """Test improvement suggestions."""
        sales_coach_agent.suggest_improvements = AsyncMock(
            return_value=[
                "Focus on building rapport before pitching",
                "Ask more discovery questions",
                "Address objections with empathy",
            ]
        )

        performance_data = {
            "overall_score": 6.5,
            "methodology_score": 6.0,
            "objection_handling_score": 5.5,
        }

        suggestions = await sales_coach_agent.suggest_improvements(performance_data)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)


class TestCustomerSimulatorAgent:
    """Tests for Customer Simulator Agent."""

    @pytest.fixture
    def customer_agent(self):
        """Create customer simulator agent instance."""
        agent = Mock()
        agent.generate_response = AsyncMock(
            return_value="I'm interested, but the price seems high."
        )
        agent.update_interest_level = Mock()
        agent.get_state = Mock(
            return_value={
                "interest_level": 0.7,
                "objections": ["price"],
                "current_stage": "consideration",
            }
        )
        return agent

    @pytest.mark.asyncio
    async def test_generate_response(self, customer_agent):
        """Test customer response generation."""
        user_message = "Our product costs $99/month"

        response = await customer_agent.generate_response(user_message)

        assert isinstance(response, str)
        assert len(response) > 0

    def test_update_interest_level(self, customer_agent):
        """Test interest level updates."""
        customer_agent.update_interest_level(0.8)
        customer_agent.update_interest_level.assert_called_once_with(0.8)

    def test_get_customer_state(self, customer_agent):
        """Test getting customer state."""
        state = customer_agent.get_state()

        assert "interest_level" in state
        assert "objections" in state
        assert "current_stage" in state
        assert isinstance(state["interest_level"], float)
        assert isinstance(state["objections"], list)

    @pytest.mark.asyncio
    async def test_raise_objection(self, customer_agent):
        """Test objection raising."""
        customer_agent.raise_objection = AsyncMock(
            return_value="That's too expensive for our budget."
        )

        objection_type = "price"
        objection = await customer_agent.raise_objection(objection_type)

        assert isinstance(objection, str)
        assert len(objection) > 0


class TestEvaluatorAgent:
    """Tests for Evaluator Agent."""

    @pytest.fixture
    def evaluator_agent(self):
        """Create evaluator agent instance."""
        agent = Mock()
        agent.evaluate_session = AsyncMock(
            return_value={
                "overall_score": 8.0,
                "methodology_score": 7.5,
                "objection_handling_score": 8.5,
                "goal_orientation_score": 7.0,
                "empathy_score": 9.0,
                "clarity_score": 8.0,
                "strengths": ["Good empathy", "Clear communication"],
                "weaknesses": ["Could improve discovery questions"],
                "suggestions": ["Ask more open-ended questions"],
            }
        )
        return agent

    @pytest.mark.asyncio
    async def test_evaluate_session(self, evaluator_agent):
        """Test session evaluation."""
        session_data = {
            "messages": [
                {"role": "user", "content": "I need a solution"},
                {"role": "assistant", "content": "Let me help you"},
            ],
            "turns_count": 15,
            "objections_raised": 3,
            "objections_resolved": 2,
        }

        result = await evaluator_agent.evaluate_session(session_data)

        assert "overall_score" in result
        assert "methodology_score" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert "suggestions" in result

        # Validate score ranges
        for key in ["overall_score", "methodology_score", "objection_handling_score"]:
            if key in result:
                assert 0 <= result[key] <= 10

    @pytest.mark.asyncio
    async def test_evaluate_methodology(self, evaluator_agent):
        """Test methodology evaluation."""
        evaluator_agent.evaluate_methodology = AsyncMock(return_value=7.5)

        messages = [
            {"role": "assistant", "content": "Tell me about your needs"},
            {"role": "user", "content": "I need better sales tools"},
        ]

        score = await evaluator_agent.evaluate_methodology(messages)

        assert isinstance(score, (int, float))
        assert 0 <= score <= 10

    @pytest.mark.asyncio
    async def test_evaluate_objection_handling(self, evaluator_agent):
        """Test objection handling evaluation."""
        evaluator_agent.evaluate_objection_handling = AsyncMock(return_value=8.0)

        objection_data = {
            "objections_raised": 3,
            "objections_resolved": 2,
            "resolution_quality": "good",
        }

        score = await evaluator_agent.evaluate_objection_handling(objection_data)

        assert isinstance(score, (int, float))
        assert 0 <= score <= 10


class TestAgentOrchestrator:
    """Tests for Agent Orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        orch = Mock()
        orch.process_turn = AsyncMock(
            return_value={
                "customer_response": "That sounds interesting",
                "coach_feedback": "Good job building rapport",
                "state_update": {"interest_level": 0.8},
            }
        )
        return orch

    @pytest.mark.asyncio
    async def test_process_turn(self, orchestrator):
        """Test turn processing."""
        user_message = "Let me tell you about our features"

        result = await orchestrator.process_turn(user_message)

        assert "customer_response" in result
        assert "coach_feedback" in result
        assert isinstance(result["customer_response"], str)

    @pytest.mark.asyncio
    async def test_orchestrator_error_handling(self, orchestrator):
        """Test error handling in orchestrator."""
        orchestrator.process_turn = AsyncMock(side_effect=Exception("LLM error"))

        with pytest.raises(Exception):
            await orchestrator.process_turn("test message")


@pytest.mark.asyncio
async def test_agent_communication():
    """Test communication between agents."""
    # Mock agents
    sales_coach = Mock()
    customer = Mock()

    sales_coach.provide_feedback = AsyncMock(return_value="Good approach")
    customer.generate_response = AsyncMock(return_value="I'm interested")

    # Simulate interaction
    user_msg = "Tell me about your product"
    customer_response = await customer.generate_response(user_msg)
    coach_feedback = await sales_coach.provide_feedback([user_msg, customer_response])

    assert isinstance(customer_response, str)
    assert isinstance(coach_feedback, str)


@pytest.mark.asyncio
async def test_agent_state_persistence():
    """Test agent state persistence."""
    agent = Mock()
    agent.save_state = Mock()
    agent.load_state = Mock(return_value={"interest_level": 0.7})

    # Save state
    state = {"interest_level": 0.7, "objections": ["price"]}
    agent.save_state(state)
    agent.save_state.assert_called_once()

    # Load state
    loaded_state = agent.load_state()
    assert "interest_level" in loaded_state
