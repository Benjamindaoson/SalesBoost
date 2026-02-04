"""
A2A Agent Base Class

Base class for agents with A2A communication capabilities.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.a2a.message_bus import A2AMessageBus
from app.a2a.protocol import (
    A2AEvent,
    A2AMessage,
    A2AQuery,
    A2ARequest,
    A2AResponse,
    MessageType,
)
from app.agents.roles.base import BaseAgent

logger = logging.getLogger(__name__)


class A2AAgent(BaseAgent):
    """
    A2A-enabled Agent Base Class

    Extends BaseAgent with agent-to-agent communication capabilities.

    Features:
    - Send/receive messages to/from other agents
    - Request-response pattern
    - Event broadcasting and subscription
    - Agent discovery
    - Automatic message handling

    Usage:
        class MyAgent(A2AAgent):
            def __init__(self, agent_id: str, message_bus: A2AMessageBus):
                super().__init__(
                    agent_id=agent_id,
                    message_bus=message_bus,
                    capabilities=["my_capability"]
                )

            async def handle_request(self, message: A2AMessage) -> Dict:
                # Handle incoming requests
                action = message.payload.get("action")
                if action == "do_something":
                    return {"result": "done"}
                raise ValueError(f"Unknown action: {action}")

            async def handle_event(self, message: A2AMessage):
                # Handle incoming events
                event_type = message.payload.get("event_type")
                logger.info(f"Received event: {event_type}")
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: A2AMessageBus,
        capabilities: Optional[List[str]] = None,
        agent_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize A2A agent

        Args:
            agent_id: Unique agent identifier
            message_bus: Message bus instance
            capabilities: List of agent capabilities
            agent_type: Type of agent (defaults to class name)
            metadata: Additional metadata
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(**kwargs)

        self.agent_id = agent_id
        self.message_bus = message_bus
        self.capabilities = capabilities or []
        self.agent_type = agent_type or self.__class__.__name__
        self.metadata = metadata or {}

        # Current conversation context
        self.current_conversation_id: Optional[str] = None

        # Message handlers
        self._message_handlers: Dict[MessageType, Any] = {
            MessageType.REQUEST: self._handle_request_message,
            MessageType.QUERY: self._handle_query_message,
            MessageType.EVENT: self._handle_event_message,
            MessageType.COMMAND: self._handle_command_message,
        }

        # Initialization flag
        self._initialized = False

    async def initialize(self):
        """
        Initialize agent and register with message bus

        Should be called before using the agent.
        """
        if self._initialized:
            logger.warning(f"Agent {self.agent_id} already initialized")
            return

        # Register with message bus
        await self.message_bus.register_agent(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            capabilities=self.capabilities,
            metadata=self.metadata,
        )

        # Subscribe to messages
        await self.message_bus.subscribe(self.agent_id, self._handle_message)

        self._initialized = True
        logger.info(f"Agent initialized: {self.agent_id} ({self.agent_type})")

    async def shutdown(self):
        """Shutdown agent and unregister from message bus"""
        if not self._initialized:
            return

        await self.message_bus.unregister_agent(self.agent_id)
        self._initialized = False
        logger.info(f"Agent shutdown: {self.agent_id}")

    async def _handle_message(self, message: A2AMessage):
        """
        Internal message handler

        Routes messages to appropriate handlers based on type.

        Args:
            message: Incoming message
        """
        try:
            handler = self._message_handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                logger.warning(
                    f"No handler for message type: {message.message_type}"
                )

        except Exception as e:
            logger.error(
                f"Error handling message {message.message_id}: {e}", exc_info=True
            )

            # Send error response if it was a request
            if message.message_type == MessageType.REQUEST:
                error_response = A2AResponse(
                    success=False, error=str(e)
                ).to_payload()
                response = message.create_response(error_response, self.agent_id)
                await self.message_bus.publish(response)

    async def _handle_request_message(self, message: A2AMessage):
        """Handle REQUEST messages"""
        try:
            # Call user-defined handler
            result = await self.handle_request(message)

            # Send response
            response_payload = A2AResponse(success=True, result=result).to_payload()
            response = message.create_response(response_payload, self.agent_id)
            await self.message_bus.publish(response)

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            # Error response already sent by _handle_message
            raise

    async def _handle_query_message(self, message: A2AMessage):
        """Handle QUERY messages"""
        try:
            # Call user-defined handler
            result = await self.handle_query(message)

            # Send response
            response_payload = A2AResponse(success=True, result=result).to_payload()
            response = message.create_response(response_payload, self.agent_id)
            await self.message_bus.publish(response)

        except Exception as e:
            logger.error(f"Error handling query: {e}")
            raise

    async def _handle_event_message(self, message: A2AMessage):
        """Handle EVENT messages"""
        await self.handle_event(message)

    async def _handle_command_message(self, message: A2AMessage):
        """Handle COMMAND messages"""
        await self.handle_command(message)

    # Methods to be overridden by subclasses

    async def handle_request(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming request

        Override this method to handle requests from other agents.

        Args:
            message: Request message

        Returns:
            Response data

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError(
            f"Agent {self.agent_type} does not handle requests"
        )

    async def handle_query(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming query

        Override this method to handle queries from other agents.

        Args:
            message: Query message

        Returns:
            Query results

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError(f"Agent {self.agent_type} does not handle queries")

    async def handle_event(self, message: A2AMessage):
        """
        Handle incoming event

        Override this method to handle events from other agents.

        Args:
            message: Event message
        """
        # Default: log event
        event_type = message.payload.get("event_type", "unknown")
        logger.debug(
            f"Agent {self.agent_id} received event: {event_type} "
            f"from {message.from_agent}"
        )

    async def handle_command(self, message: A2AMessage):
        """
        Handle incoming command

        Override this method to handle commands from other agents.

        Args:
            message: Command message
        """
        logger.warning(f"Agent {self.agent_type} does not handle commands")

    # Convenience methods for sending messages

    async def send_request(
        self,
        to_agent: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> A2AMessage:
        """
        Send a request to another agent and wait for response

        Args:
            to_agent: Target agent ID
            action: Action to perform
            parameters: Action parameters
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            asyncio.TimeoutError: If no response within timeout
        """
        request = A2ARequest(
            action=action, parameters=parameters or {}, timeout=timeout
        )

        message = request.to_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            conversation_id=self.current_conversation_id or str(uuid.uuid4()),
        )

        response = await self.message_bus.request(message, timeout=timeout)
        return response

    async def send_query(
        self,
        to_agent: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        timeout: float = 30.0,
    ) -> A2AMessage:
        """
        Send a query to another agent

        Args:
            to_agent: Target agent ID
            query: Query string
            filters: Query filters
            limit: Result limit
            timeout: Timeout in seconds

        Returns:
            Response message
        """
        query_obj = A2AQuery(query=query, filters=filters or {}, limit=limit)

        message = query_obj.to_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            conversation_id=self.current_conversation_id or str(uuid.uuid4()),
        )

        response = await self.message_bus.request(message, timeout=timeout)
        return response

    async def broadcast_event(
        self, event_type: str, data: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast an event to all agents

        Args:
            event_type: Type of event
            data: Event data
        """
        event = A2AEvent(event_type=event_type, data=data or {})

        message = event.to_message(
            from_agent=self.agent_id,
            conversation_id=self.current_conversation_id or "system",
            to_agent=None,  # Broadcast
        )

        await self.message_bus.publish(message)

    async def send_event(
        self, to_agent: str, event_type: str, data: Optional[Dict[str, Any]] = None
    ):
        """
        Send an event to a specific agent

        Args:
            to_agent: Target agent ID
            event_type: Type of event
            data: Event data
        """
        event = A2AEvent(event_type=event_type, data=data or {})

        message = event.to_message(
            from_agent=self.agent_id,
            conversation_id=self.current_conversation_id or str(uuid.uuid4()),
            to_agent=to_agent,
        )

        await self.message_bus.publish(message)

    async def discover_agents(
        self, capability: Optional[str] = None, agent_type: Optional[str] = None
    ) -> List[str]:
        """
        Discover agents by capability or type

        Args:
            capability: Filter by capability
            agent_type: Filter by agent type

        Returns:
            List of agent IDs
        """
        agents = await self.message_bus.discover_agents(capability, agent_type)
        return [agent.agent_id for agent in agents]

    def set_conversation_context(self, conversation_id: str):
        """
        Set current conversation context

        Args:
            conversation_id: Conversation identifier
        """
        self.current_conversation_id = conversation_id
