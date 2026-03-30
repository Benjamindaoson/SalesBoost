"""
Test Suite for A2A Integration

Tests for A2A message bus, agents, and communication.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.a2a.protocol import (
    A2AMessage,
    A2ARequest,
    A2AResponse,
    A2AEvent,
    MessageType,
    AgentInfo,
)
from app.a2a.message_bus import A2AMessageBus
from app.a2a.agent_base import A2AAgent
from app.agents.autonomous.sdr_agent_a2a import SDRAgentA2A
from app.agents.roles.coach_agent_a2a import CoachAgentA2A
from app.agents.roles.compliance_agent_a2a import ComplianceAgentA2A


@pytest.fixture
async def redis_client():
    """Create a mock Redis client"""
    client = AsyncMock()
    client.ping = AsyncMock()
    client.publish = AsyncMock()
    client.hset = AsyncMock()
    client.hget = AsyncMock()
    client.hgetall = AsyncMock(return_value={})
    client.hdel = AsyncMock()
    client.lpush = AsyncMock()
    client.lrange = AsyncMock(return_value=[])
    client.expire = AsyncMock()
    client.delete = AsyncMock()
    client.hlen = AsyncMock(return_value=0)
    client.pubsub = MagicMock()
    return client


@pytest.fixture
async def message_bus(redis_client):
    """Create a message bus with mock Redis"""
    bus = A2AMessageBus(redis_client)
    return bus


class TestA2AProtocol:
    """Tests for A2A Protocol"""

    def test_message_creation(self):
        """Test creating A2A message"""
        message = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="agent_1",
            to_agent="agent_2",
            conversation_id="conv_123",
            payload={"action": "test"},
        )

        assert message.message_type == MessageType.REQUEST
        assert message.from_agent == "agent_1"
        assert message.to_agent == "agent_2"

    def test_message_to_dict(self):
        """Test message serialization"""
        message = A2AMessage(
            message_type=MessageType.EVENT,
            from_agent="agent_1",
            payload={"event_type": "test_event"},
        )

        data = message.to_dict()

        assert data["message_type"] == "event"
        assert data["from_agent"] == "agent_1"
        assert "message_id" in data

    def test_message_from_dict(self):
        """Test message deserialization"""
        data = {
            "message_id": "msg_123",
            "message_type": "request",
            "from_agent": "agent_1",
            "to_agent": "agent_2",
            "conversation_id": "conv_123",
            "timestamp": 1234567890.0,
            "payload": {"action": "test"},
        }

        message = A2AMessage.from_dict(data)

        assert message.message_id == "msg_123"
        assert message.message_type == MessageType.REQUEST
        assert message.from_agent == "agent_1"

    def test_create_response(self):
        """Test creating response message"""
        request = A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent="agent_1",
            to_agent="agent_2",
            conversation_id="conv_123",
            payload={"action": "test"},
        )

        response = request.create_response(
            payload={"result": "success"}, from_agent="agent_2"
        )

        assert response.message_type == MessageType.RESPONSE
        assert response.from_agent == "agent_2"
        assert response.to_agent == "agent_1"
        assert response.reply_to == request.message_id


class TestA2AMessageBus:
    """Tests for A2A Message Bus"""

    @pytest.mark.asyncio
    async def test_register_agent(self, message_bus):
        """Test agent registration"""
        await message_bus.register_agent(
            agent_id="test_agent",
            agent_type="TestAgent",
            capabilities=["test"],
        )

        assert "test_agent" in message_bus.agent_registry
        message_bus.redis.hset.assert_called()

    @pytest.mark.asyncio
    async def test_publish_message(self, message_bus):
        """Test publishing message"""
        message = A2AMessage(
            message_type=MessageType.EVENT,
            from_agent="agent_1",
            to_agent="agent_2",
            conversation_id="conv_123",
            payload={"event_type": "test"},
        )

        await message_bus.publish(message)

        message_bus.redis.publish.assert_called()
        message_bus.redis.lpush.assert_called()

    @pytest.mark.asyncio
    async def test_discover_agents(self, message_bus):
        """Test agent discovery"""
        # Mock Redis response
        message_bus.redis.hgetall = AsyncMock(
            return_value={
                "agent_1": '{"agent_id":"agent_1","agent_type":"TestAgent","capabilities":["test"],"status":"online"}',
                "agent_2": '{"agent_id":"agent_2","agent_type":"OtherAgent","capabilities":["other"],"status":"online"}',
            }
        )

        agents = await message_bus.discover_agents(capability="test")

        assert len(agents) == 1
        assert agents[0].agent_id == "agent_1"


class TestA2AAgent:
    """Tests for A2A Agent Base Class"""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, message_bus):
        """Test agent initialization"""

        class TestAgent(A2AAgent):
            async def handle_request(self, message):
                return {"result": "test"}

        agent = TestAgent(
            agent_id="test_agent",
            message_bus=message_bus,
            capabilities=["test"],
        )

        await agent.initialize()

        assert agent._initialized
        assert "test_agent" in message_bus.agent_registry

    @pytest.mark.asyncio
    async def test_send_request(self, message_bus):
        """Test sending request"""

        class TestAgent(A2AAgent):
            async def handle_request(self, message):
                return {"result": "test"}

        agent = TestAgent(
            agent_id="test_agent",
            message_bus=message_bus,
            capabilities=["test"],
        )
        await agent.initialize()

        # Mock request method
        message_bus.request = AsyncMock(
            return_value=A2AMessage(
                message_type=MessageType.RESPONSE,
                from_agent="other_agent",
                to_agent="test_agent",
                payload={"success": True, "result": {"data": "test"}},
            )
        )

        response = await agent.send_request(
            to_agent="other_agent", action="test_action", parameters={}
        )

        assert response.message_type == MessageType.RESPONSE
        message_bus.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_event(self, message_bus):
        """Test broadcasting event"""

        class TestAgent(A2AAgent):
            async def handle_request(self, message):
                return {}

        agent = TestAgent(
            agent_id="test_agent",
            message_bus=message_bus,
            capabilities=["test"],
        )
        await agent.initialize()

        await agent.broadcast_event(event_type="test_event", data={"key": "value"})

        message_bus.publish.assert_called()


class TestSDRAgentA2A:
    """Tests for SDR Agent A2A"""

    @pytest.mark.asyncio
    async def test_generate_response(self, message_bus):
        """Test generating sales response"""
        agent = SDRAgentA2A(agent_id="sdr_001", message_bus=message_bus)
        await agent.initialize()

        # Mock discover_agents to return empty list
        message_bus.discover_agents = AsyncMock(return_value=[])

        result = await agent._generate_response(
            {
                "customer_message": "Tell me about your product",
                "context": {},
                "stage": "discovery",
            }
        )

        assert "message" in result
        assert result["stage"] == "discovery"

    @pytest.mark.asyncio
    async def test_handle_objection(self, message_bus):
        """Test handling objection"""
        agent = SDRAgentA2A(agent_id="sdr_001", message_bus=message_bus)
        await agent.initialize()

        # Mock discover_agents
        message_bus.discover_agents = AsyncMock(return_value=[])

        result = await agent._handle_objection(
            {"objection": "Too expensive", "objection_type": "price"}
        )

        assert result["success"]
        assert result["objection_type"] == "price"


class TestCoachAgentA2A:
    """Tests for Coach Agent A2A"""

    @pytest.mark.asyncio
    async def test_get_suggestion(self, message_bus):
        """Test getting coaching suggestion"""
        agent = CoachAgentA2A(agent_id="coach_001", message_bus=message_bus)
        await agent.initialize()

        result = await agent._get_suggestion(
            {
                "customer_message": "I'm not sure about this",
                "context": {},
                "stage": "discovery",
            }
        )

        assert "recommended_approach" in result
        assert "key_points" in result

    @pytest.mark.asyncio
    async def test_evaluate_response(self, message_bus):
        """Test evaluating sales response"""
        agent = CoachAgentA2A(agent_id="coach_001", message_bus=message_bus)
        await agent.initialize()

        result = await agent._evaluate_response(
            {
                "response": "I understand your concern...",
                "customer_message": "Too expensive",
            }
        )

        assert "overall_score" in result
        assert "strengths" in result
        assert "weaknesses" in result


class TestComplianceAgentA2A:
    """Tests for Compliance Agent A2A"""

    @pytest.mark.asyncio
    async def test_check_compliance(self, message_bus):
        """Test compliance check"""
        agent = ComplianceAgentA2A(
            agent_id="compliance_001", message_bus=message_bus
        )
        await agent.initialize()

        # Test compliant content
        result = await agent._check_compliance(
            {"content": "Our product can help you achieve your goals"}
        )

        assert result["compliant"]
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_check_compliance_violation(self, message_bus):
        """Test compliance violation detection"""
        agent = ComplianceAgentA2A(
            agent_id="compliance_001", message_bus=message_bus
        )
        await agent.initialize()

        # Test non-compliant content
        result = await agent._check_compliance(
            {"content": "This is guaranteed returns with no risk"}
        )

        assert not result["compliant"]
        assert len(result["violations"]) > 0

    @pytest.mark.asyncio
    async def test_check_deal(self, message_bus):
        """Test deal compliance check"""
        agent = ComplianceAgentA2A(
            agent_id="compliance_001", message_bus=message_bus
        )
        await agent.initialize()

        # Test deal with excessive discount
        result = await agent._check_deal(
            {"deal_info": {"value": 10000, "discount": 40}}
        )

        assert not result["compliant"]
        assert len(result["violations"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
