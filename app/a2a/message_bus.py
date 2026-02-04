"""
A2A Message Bus Implementation

Redis-based message bus for agent-to-agent communication.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from redis.asyncio import Redis

from app.a2a.protocol import A2AMessage, AgentInfo, MessageType

logger = logging.getLogger(__name__)

# Type alias for message handler
MessageHandler = Callable[[A2AMessage], Coroutine[Any, Any, None]]


class A2AMessageBus:
    """
    A2A Message Bus

    Redis-based message bus for agent-to-agent communication.
    Supports direct messaging, broadcasting, and agent discovery.

    Features:
    - Direct agent-to-agent messaging
    - Broadcast messaging
    - Agent registration and discovery
    - Message history and persistence
    - Priority-based message delivery
    - Request-response pattern with timeout

    Usage:
        bus = A2AMessageBus(redis_client)

        # Register agent
        await bus.register_agent(
            agent_id="sdr_001",
            agent_type="SDRAgent",
            capabilities=["sales", "objection_handling"]
        )

        # Subscribe to messages
        await bus.subscribe("sdr_001", message_handler)

        # Send message
        await bus.publish(message)

        # Request-response
        response = await bus.request(request_message, timeout=30.0)
    """

    def __init__(
        self,
        redis_client: Redis,
        channel_prefix: str = "a2a",
        history_ttl: int = 3600,  # 1 hour
    ):
        """
        Initialize message bus

        Args:
            redis_client: Redis client instance
            channel_prefix: Prefix for Redis channels
            history_ttl: TTL for message history in seconds
        """
        self.redis = redis_client
        self.channel_prefix = channel_prefix
        self.history_ttl = history_ttl

        # Agent registry
        self.agent_registry: Dict[str, AgentInfo] = {}

        # Active subscriptions
        self.subscriptions: Dict[str, asyncio.Task] = {}

        # Pending requests (for request-response pattern)
        self.pending_requests: Dict[str, asyncio.Future] = {}

        logger.info("A2A Message Bus initialized")

    def _get_channel(self, agent_id: Optional[str] = None) -> str:
        """
        Get Redis channel name

        Args:
            agent_id: Agent ID (None for broadcast)

        Returns:
            Channel name
        """
        if agent_id:
            return f"{self.channel_prefix}:{agent_id}"
        return f"{self.channel_prefix}:broadcast"

    def _get_response_channel(self, message_id: str) -> str:
        """Get response channel for a message"""
        return f"{self.channel_prefix}:response:{message_id}"

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register an agent with the message bus

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent
            capabilities: List of agent capabilities
            metadata: Additional metadata
        """
        agent_info = AgentInfo(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            status="online",
            metadata=metadata or {},
            last_seen=time.time(),
        )

        # Store in local registry
        self.agent_registry[agent_id] = agent_info

        # Store in Redis
        await self.redis.hset(
            f"{self.channel_prefix}:agents",
            agent_id,
            json.dumps(agent_info.to_dict()),
        )

        # Publish agent online event
        event = A2AMessage(
            message_type=MessageType.EVENT,
            from_agent=agent_id,
            to_agent=None,  # Broadcast
            conversation_id="system",
            payload={
                "event_type": "agent_online",
                "agent_info": agent_info.to_dict(),
            },
        )
        await self.publish(event)

        logger.info(f"Agent registered: {agent_id} ({agent_type})")

    async def unregister_agent(self, agent_id: str):
        """
        Unregister an agent

        Args:
            agent_id: Agent identifier
        """
        if agent_id in self.agent_registry:
            # Publish agent offline event
            event = A2AMessage(
                message_type=MessageType.EVENT,
                from_agent=agent_id,
                to_agent=None,
                conversation_id="system",
                payload={"event_type": "agent_offline"},
            )
            await self.publish(event)

            # Remove from registries
            del self.agent_registry[agent_id]
            await self.redis.hdel(f"{self.channel_prefix}:agents", agent_id)

            # Cancel subscription
            if agent_id in self.subscriptions:
                self.subscriptions[agent_id].cancel()
                del self.subscriptions[agent_id]

            logger.info(f"Agent unregistered: {agent_id}")

    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Get agent information

        Args:
            agent_id: Agent identifier

        Returns:
            Agent info or None if not found
        """
        # Check local registry first
        if agent_id in self.agent_registry:
            return self.agent_registry[agent_id]

        # Check Redis
        data = await self.redis.hget(f"{self.channel_prefix}:agents", agent_id)
        if data:
            return AgentInfo.from_dict(json.loads(data))

        return None

    async def discover_agents(
        self, capability: Optional[str] = None, agent_type: Optional[str] = None
    ) -> List[AgentInfo]:
        """
        Discover agents by capability or type

        Args:
            capability: Filter by capability
            agent_type: Filter by agent type

        Returns:
            List of matching agents
        """
        # Get all agents from Redis
        agents_data = await self.redis.hgetall(f"{self.channel_prefix}:agents")

        agents = []
        for agent_data in agents_data.values():
            agent_info = AgentInfo.from_dict(json.loads(agent_data))

            # Apply filters
            if capability and capability not in agent_info.capabilities:
                continue
            if agent_type and agent_info.agent_type != agent_type:
                continue

            agents.append(agent_info)

        return agents

    async def publish(self, message: A2AMessage):
        """
        Publish a message

        Args:
            message: Message to publish
        """
        # Get target channel
        channel = self._get_channel(message.to_agent)

        # Serialize message
        message_json = json.dumps(message.to_dict())

        # Publish to Redis
        await self.redis.publish(channel, message_json)

        # Store in history
        history_key = f"{self.channel_prefix}:history:{message.conversation_id}"
        await self.redis.lpush(history_key, message_json)
        await self.redis.expire(history_key, self.history_ttl)

        logger.debug(
            f"Published message: {message.message_type} from {message.from_agent} "
            f"to {message.to_agent or 'broadcast'}"
        )

    async def subscribe(self, agent_id: str, handler: MessageHandler):
        """
        Subscribe to messages for an agent

        Args:
            agent_id: Agent identifier
            handler: Async function to handle messages
        """
        if agent_id in self.subscriptions:
            logger.warning(f"Agent {agent_id} already subscribed")
            return

        # Create subscription task
        task = asyncio.create_task(self._subscription_loop(agent_id, handler))
        self.subscriptions[agent_id] = task

        logger.info(f"Agent subscribed: {agent_id}")

    async def _subscription_loop(self, agent_id: str, handler: MessageHandler):
        """
        Subscription loop for an agent

        Args:
            agent_id: Agent identifier
            handler: Message handler function
        """
        # Subscribe to direct and broadcast channels
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(
            self._get_channel(agent_id), self._get_channel(None)
        )

        try:
            async for redis_message in pubsub.listen():
                if redis_message["type"] != "message":
                    continue

                try:
                    # Parse message
                    message = A2AMessage.from_dict(
                        json.loads(redis_message["data"])
                    )

                    # Skip messages from self
                    if message.from_agent == agent_id:
                        continue

                    # Send ACK if required
                    if message.requires_ack:
                        ack = message.create_ack(agent_id)
                        await self.publish(ack)

                    # Handle response messages
                    if (
                        message.message_type == MessageType.RESPONSE
                        and message.reply_to in self.pending_requests
                    ):
                        # Resolve pending request
                        future = self.pending_requests[message.reply_to]
                        if not future.done():
                            future.set_result(message)
                        continue

                    # Call handler
                    await handler(message)

                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info(f"Subscription cancelled for agent: {agent_id}")
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    async def request(
        self, message: A2AMessage, timeout: float = 30.0
    ) -> A2AMessage:
        """
        Send a request and wait for response

        Args:
            message: Request message
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            asyncio.TimeoutError: If no response within timeout
        """
        # Create future for response
        future: asyncio.Future[A2AMessage] = asyncio.Future()
        self.pending_requests[message.message_id] = future

        try:
            # Publish request
            await self.publish(message)

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            logger.error(
                f"Request timeout: {message.message_id} to {message.to_agent}"
            )
            raise

        finally:
            # Clean up
            if message.message_id in self.pending_requests:
                del self.pending_requests[message.message_id]

    async def get_conversation_history(
        self, conversation_id: str, limit: int = 100
    ) -> List[A2AMessage]:
        """
        Get conversation history

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages

        Returns:
            List of messages in chronological order
        """
        history_key = f"{self.channel_prefix}:history:{conversation_id}"

        # Get messages from Redis
        messages_data = await self.redis.lrange(history_key, 0, limit - 1)

        # Parse messages
        messages = []
        for message_data in reversed(messages_data):  # Reverse for chronological order
            try:
                message = A2AMessage.from_dict(json.loads(message_data))
                messages.append(message)
            except Exception as e:
                logger.error(f"Error parsing message from history: {e}")

        return messages

    async def clear_conversation_history(self, conversation_id: str):
        """
        Clear conversation history

        Args:
            conversation_id: Conversation identifier
        """
        history_key = f"{self.channel_prefix}:history:{conversation_id}"
        await self.redis.delete(history_key)
        logger.info(f"Cleared conversation history: {conversation_id}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics

        Returns:
            Statistics dictionary
        """
        agent_count = await self.redis.hlen(f"{self.channel_prefix}:agents")

        return {
            "registered_agents": agent_count,
            "active_subscriptions": len(self.subscriptions),
            "pending_requests": len(self.pending_requests),
        }

    async def shutdown(self):
        """Shutdown message bus"""
        logger.info("Shutting down A2A Message Bus")

        # Cancel all subscriptions
        for task in self.subscriptions.values():
            task.cancel()

        # Wait for tasks to complete
        if self.subscriptions:
            await asyncio.gather(*self.subscriptions.values(), return_exceptions=True)

        self.subscriptions.clear()
        self.pending_requests.clear()

        logger.info("A2A Message Bus shutdown complete")
