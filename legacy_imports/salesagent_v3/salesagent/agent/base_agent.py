"""Base Agent class for multi-agent system.

This module provides the foundation for all agents in the system.
Each agent can receive messages, process them, and send responses.
"""
from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import structlog

log = structlog.get_logger()


class AgentStatus(Enum):
    """Agent status enum."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class AgentCapability(Enum):
    """Agent capability types."""
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    RETRIEVAL = "retrieval"
    RESPONSE_GENERATION = "response_generation"
    COMPLIANCE_CHECK = "compliance_check"
    STRATEGY_PLANNING = "strategy_planning"


class Message:
    """Message passed between agents."""

    def __init__(
        self,
        from_agent: str,
        to_agent: str,
        content: dict[str, Any],
        message_type: str = "request",
        message_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.correlation_id = correlation_id or self.message_id
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.content = content
        self.message_type = message_type  # request, response, broadcast, error
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            correlation_id=data["correlation_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            content=data["content"],
            message_type=data["message_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system.

    Each agent has:
    - A unique name
    - A role description
    - A set of capabilities
    - A message queue for receiving messages
    - Methods to process messages and send responses

    Usage:
        class MyAgent(BaseAgent):
            async def process(self, message: Message) -> dict[str, Any]:
                # Process the message
                return {"result": "..."}

        agent = MyAgent(name="my_agent", role="My custom agent")
        await agent.start()
    """

    def __init__(
        self,
        name: str,
        role: str,
        capabilities: list[AgentCapability],
        max_queue_size: int = 100,
    ):
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.status = AgentStatus.IDLE
        self.message_queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=max_queue_size)
        self.message_bus: Optional[MessageBus] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Metrics
        self.messages_processed = 0
        self.messages_failed = 0
        self.total_processing_time = 0.0

        log.info(
            "Agent initialized",
            agent_name=self.name,
            role=self.role,
            capabilities=[c.value for c in self.capabilities],
        )

    async def start(self):
        """Start the agent's message processing loop."""
        if self._running:
            log.warning("Agent already running", agent_name=self.name)
            return

        self._running = True
        self.status = AgentStatus.IDLE
        self._task = asyncio.create_task(self._run())
        log.info("Agent started", agent_name=self.name)

    async def stop(self):
        """Stop the agent's message processing loop."""
        if not self._running:
            return

        self._running = False
        self.status = AgentStatus.STOPPED

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        log.info("Agent stopped", agent_name=self.name)

    async def _run(self):
        """Main message processing loop."""
        while self._running:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )

                await self._handle_message(message)

            except asyncio.TimeoutError:
                # No message received, continue
                continue
            except Exception as exc:
                log.error(
                    "Error in agent run loop",
                    agent_name=self.name,
                    error=str(exc),
                    exc_info=True,
                )

    async def _handle_message(self, message: Message):
        """Handle a single message."""
        self.status = AgentStatus.BUSY
        start_time = datetime.now()

        log.info(
            "Processing message",
            agent_name=self.name,
            message_id=message.message_id,
            from_agent=message.from_agent,
            message_type=message.message_type,
        )

        try:
            # Process the message
            result = await self.process(message)

            # Send response if this was a request
            if message.message_type == "request":
                response = Message(
                    from_agent=self.name,
                    to_agent=message.from_agent,
                    content=result,
                    message_type="response",
                    correlation_id=message.correlation_id,
                )
                await self.send_message(response)

            # Update metrics
            self.messages_processed += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            self.total_processing_time += processing_time

            log.info(
                "Message processed successfully",
                agent_name=self.name,
                message_id=message.message_id,
                processing_time=processing_time,
            )

        except Exception as exc:
            self.messages_failed += 1
            self.status = AgentStatus.ERROR

            log.error(
                "Error processing message",
                agent_name=self.name,
                message_id=message.message_id,
                error=str(exc),
                exc_info=True,
            )

            # Send error response
            if message.message_type == "request":
                error_response = Message(
                    from_agent=self.name,
                    to_agent=message.from_agent,
                    content={"error": str(exc)},
                    message_type="error",
                    correlation_id=message.correlation_id,
                )
                await self.send_message(error_response)

        finally:
            self.status = AgentStatus.IDLE

    @abstractmethod
    async def process(self, message: Message) -> dict[str, Any]:
        """Process a message and return the result.

        This method must be implemented by subclasses.

        Args:
            message: The message to process

        Returns:
            A dictionary containing the processing result
        """
        pass

    async def receive_message(self, message: Message):
        """Receive a message and add it to the queue.

        Args:
            message: The message to receive
        """
        try:
            await self.message_queue.put(message)
            log.debug(
                "Message received",
                agent_name=self.name,
                message_id=message.message_id,
                from_agent=message.from_agent,
            )
        except asyncio.QueueFull:
            log.error(
                "Message queue full, dropping message",
                agent_name=self.name,
                message_id=message.message_id,
            )

    async def send_message(self, message: Message):
        """Send a message to another agent via the message bus.

        Args:
            message: The message to send
        """
        if not self.message_bus:
            log.error(
                "Cannot send message: message bus not set",
                agent_name=self.name,
            )
            return

        await self.message_bus.publish(message)

        log.debug(
            "Message sent",
            agent_name=self.name,
            message_id=message.message_id,
            to_agent=message.to_agent,
        )

    def set_message_bus(self, message_bus: MessageBus):
        """Set the message bus for this agent.

        Args:
            message_bus: The message bus to use
        """
        self.message_bus = message_bus

    def get_metrics(self) -> dict[str, Any]:
        """Get agent metrics.

        Returns:
            Dictionary containing agent metrics
        """
        avg_processing_time = (
            self.total_processing_time / self.messages_processed
            if self.messages_processed > 0
            else 0.0
        )

        return {
            "agent_name": self.name,
            "status": self.status.value,
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "avg_processing_time": avg_processing_time,
            "success_rate": (
                (self.messages_processed - self.messages_failed) / self.messages_processed
                if self.messages_processed > 0
                else 0.0
            ),
        }


class MessageBus:
    """Message bus for agent communication.

    The message bus handles routing messages between agents.
    Agents subscribe to the bus and receive messages addressed to them.

    Usage:
        bus = MessageBus()
        bus.subscribe(agent1)
        bus.subscribe(agent2)

        # Agent1 sends message to Agent2
        message = Message(from_agent="agent1", to_agent="agent2", content={...})
        await bus.publish(message)
    """

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.message_history: list[Message] = []
        self.max_history = 1000

        log.info("MessageBus initialized")

    def subscribe(self, agent: BaseAgent):
        """Subscribe an agent to the message bus.

        Args:
            agent: The agent to subscribe
        """
        self.agents[agent.name] = agent
        agent.set_message_bus(self)

        log.info(
            "Agent subscribed to message bus",
            agent_name=agent.name,
        )

    def unsubscribe(self, agent_name: str):
        """Unsubscribe an agent from the message bus.

        Args:
            agent_name: The name of the agent to unsubscribe
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            log.info(
                "Agent unsubscribed from message bus",
                agent_name=agent_name,
            )

    async def publish(self, message: Message):
        """Publish a message to the bus.

        The message will be routed to the target agent.

        Args:
            message: The message to publish
        """
        # Add to history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

        # Route to target agent
        if message.to_agent == "broadcast":
            # Broadcast to all agents except sender
            for agent_name, agent in self.agents.items():
                if agent_name != message.from_agent:
                    await agent.receive_message(message)
        else:
            # Send to specific agent
            if message.to_agent in self.agents:
                await self.agents[message.to_agent].receive_message(message)
            else:
                log.error(
                    "Target agent not found",
                    to_agent=message.to_agent,
                    message_id=message.message_id,
                )

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get an agent by name.

        Args:
            agent_name: The name of the agent

        Returns:
            The agent, or None if not found
        """
        return self.agents.get(agent_name)

    def get_all_agents(self) -> list[BaseAgent]:
        """Get all subscribed agents.

        Returns:
            List of all agents
        """
        return list(self.agents.values())

    def get_message_history(self, limit: int = 100) -> list[Message]:
        """Get recent message history.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of recent messages
        """
        return self.message_history[-limit:]
