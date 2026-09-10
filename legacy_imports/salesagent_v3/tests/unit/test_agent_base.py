"""Tests for base agent and message bus."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from salesagent.agent.base_agent import (
    AgentCapability,
    AgentStatus,
    BaseAgent,
    Message,
    MessageBus,
)


class TestAgent(BaseAgent):
    """Test agent for unit tests."""

    def __init__(self, name: str = "test_agent"):
        super().__init__(
            name=name,
            role="Test agent",
            capabilities=[AgentCapability.REASONING],
        )
        self.processed_messages = []

    async def process(self, message: Message) -> dict[str, Any]:
        """Process message by echoing content."""
        self.processed_messages.append(message)
        return {"echo": message.content}


@pytest.mark.asyncio
async def test_message_creation():
    """Test message creation and serialization."""
    message = Message(
        from_agent="agent1",
        to_agent="agent2",
        content={"key": "value"},
        message_type="request",
    )

    assert message.from_agent == "agent1"
    assert message.to_agent == "agent2"
    assert message.content == {"key": "value"}
    assert message.message_type == "request"
    assert message.message_id is not None
    assert message.correlation_id is not None

    # Test serialization
    data = message.to_dict()
    assert data["from_agent"] == "agent1"
    assert data["to_agent"] == "agent2"

    # Test deserialization
    message2 = Message.from_dict(data)
    assert message2.from_agent == message.from_agent
    assert message2.to_agent == message.to_agent
    assert message2.content == message.content


@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initialization."""
    agent = TestAgent(name="test1")

    assert agent.name == "test1"
    assert agent.role == "Test agent"
    assert AgentCapability.REASONING in agent.capabilities
    assert agent.status == AgentStatus.IDLE
    assert agent.messages_processed == 0


@pytest.mark.asyncio
async def test_agent_start_stop():
    """Test agent start and stop."""
    agent = TestAgent()

    # Start agent
    await agent.start()
    assert agent.status == AgentStatus.IDLE
    assert agent._running is True

    # Stop agent
    await agent.stop()
    assert agent.status == AgentStatus.STOPPED
    assert agent._running is False


@pytest.mark.asyncio
async def test_agent_message_processing():
    """Test agent message processing."""
    agent = TestAgent()
    await agent.start()

    # Create message
    message = Message(
        from_agent="sender",
        to_agent="test_agent",
        content={"data": "test"},
        message_type="request",
    )

    # Send message to agent
    await agent.receive_message(message)

    # Wait for processing
    await asyncio.sleep(0.1)

    # Check message was processed
    assert len(agent.processed_messages) == 1
    assert agent.messages_processed == 1
    assert agent.processed_messages[0].content == {"data": "test"}

    await agent.stop()


@pytest.mark.asyncio
async def test_message_bus_subscribe():
    """Test message bus subscription."""
    bus = MessageBus()
    agent1 = TestAgent(name="agent1")
    agent2 = TestAgent(name="agent2")

    bus.subscribe(agent1)
    bus.subscribe(agent2)

    assert bus.get_agent("agent1") == agent1
    assert bus.get_agent("agent2") == agent2
    assert len(bus.get_all_agents()) == 2


@pytest.mark.asyncio
async def test_message_bus_publish():
    """Test message bus publishing."""
    bus = MessageBus()
    agent1 = TestAgent(name="agent1")
    agent2 = TestAgent(name="agent2")

    bus.subscribe(agent1)
    bus.subscribe(agent2)

    await agent1.start()
    await agent2.start()

    # Send message from agent1 to agent2
    message = Message(
        from_agent="agent1",
        to_agent="agent2",
        content={"hello": "world"},
        message_type="request",
    )

    await bus.publish(message)

    # Wait for processing
    await asyncio.sleep(0.1)

    # Check agent2 received and processed message
    assert len(agent2.processed_messages) == 1
    assert agent2.processed_messages[0].content == {"hello": "world"}

    await agent1.stop()
    await agent2.stop()


@pytest.mark.asyncio
async def test_message_bus_broadcast():
    """Test message bus broadcast."""
    bus = MessageBus()
    agent1 = TestAgent(name="agent1")
    agent2 = TestAgent(name="agent2")
    agent3 = TestAgent(name="agent3")

    bus.subscribe(agent1)
    bus.subscribe(agent2)
    bus.subscribe(agent3)

    await agent1.start()
    await agent2.start()
    await agent3.start()

    # Broadcast message from agent1
    message = Message(
        from_agent="agent1",
        to_agent="broadcast",
        content={"announcement": "hello all"},
        message_type="broadcast",
    )

    await bus.publish(message)

    # Wait for processing
    await asyncio.sleep(0.1)

    # Check agent2 and agent3 received message (but not agent1)
    assert len(agent1.processed_messages) == 0
    assert len(agent2.processed_messages) == 1
    assert len(agent3.processed_messages) == 1

    await agent1.stop()
    await agent2.stop()
    await agent3.stop()


@pytest.mark.asyncio
async def test_agent_metrics():
    """Test agent metrics collection."""
    agent = TestAgent()
    await agent.start()

    # Process some messages
    for i in range(5):
        message = Message(
            from_agent="sender",
            to_agent="test_agent",
            content={"index": i},
            message_type="request",
        )
        await agent.receive_message(message)

    # Wait for processing
    await asyncio.sleep(0.2)

    # Check metrics
    metrics = agent.get_metrics()
    assert metrics["agent_name"] == "test_agent"
    assert metrics["messages_processed"] == 5
    assert metrics["messages_failed"] == 0
    assert metrics["success_rate"] == 1.0
    assert metrics["avg_processing_time"] > 0

    await agent.stop()


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test agent error handling."""

    class ErrorAgent(BaseAgent):
        """Agent that always raises an error."""

        def __init__(self):
            super().__init__(
                name="error_agent",
                role="Error agent",
                capabilities=[AgentCapability.REASONING],
            )

        async def process(self, message: Message) -> dict[str, Any]:
            raise ValueError("Test error")

    agent = ErrorAgent()
    await agent.start()

    # Send message that will cause error
    message = Message(
        from_agent="sender",
        to_agent="error_agent",
        content={"data": "test"},
        message_type="request",
    )

    await agent.receive_message(message)

    # Wait for processing
    await asyncio.sleep(0.1)

    # Check error was handled
    assert agent.messages_failed == 1
    assert agent.messages_processed == 0

    await agent.stop()


@pytest.mark.asyncio
async def test_message_history():
    """Test message bus history."""
    bus = MessageBus()
    agent1 = TestAgent(name="agent1")
    agent2 = TestAgent(name="agent2")

    bus.subscribe(agent1)
    bus.subscribe(agent2)

    # Send multiple messages
    for i in range(5):
        message = Message(
            from_agent="agent1",
            to_agent="agent2",
            content={"index": i},
        )
        await bus.publish(message)

    # Check history
    history = bus.get_message_history(limit=10)
    assert len(history) == 5
    assert history[0].content["index"] == 0
    assert history[4].content["index"] == 4


@pytest.mark.asyncio
async def test_agent_request_response():
    """Test request-response pattern between agents."""
    bus = MessageBus()
    agent1 = TestAgent(name="agent1")
    agent2 = TestAgent(name="agent2")

    bus.subscribe(agent1)
    bus.subscribe(agent2)

    await agent1.start()
    await agent2.start()

    # Agent1 sends request to agent2
    request = Message(
        from_agent="agent1",
        to_agent="agent2",
        content={"question": "hello"},
        message_type="request",
    )

    await bus.publish(request)

    # Wait for processing and response
    await asyncio.sleep(0.2)

    # Check agent2 processed request
    assert len(agent2.processed_messages) == 1

    # Check agent1 received response
    # (Response is automatically sent back by agent2)
    assert len(agent1.processed_messages) == 1
    assert agent1.processed_messages[0].message_type == "response"
    assert agent1.processed_messages[0].content["echo"]["question"] == "hello"

    await agent1.stop()
    await agent2.stop()
