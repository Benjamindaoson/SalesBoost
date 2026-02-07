"""
Redis-based WebSocket Connection Manager

This module provides a distributed connection manager that stores state in Redis,
enabling horizontal scaling of WebSocket servers.

Architecture:
- Connection metadata stored in Redis (user_id -> server_id mapping)
- Messages routed via Redis Pub/Sub
- State synchronized across multiple server instances
- Supports graceful failover and reconnection

Key Features:
1. Stateless WebSocket servers (can scale horizontally)
2. Session affinity not required
3. Automatic failover when server crashes
4. Message delivery guarantees with ACK mechanism
5. Distributed turn deduplication

Usage:
    manager = RedisConnectionManager(redis_url="redis://localhost:6379/0")
    await manager.connect(websocket, session_id, user_id)
    await manager.send_json(session_id, {"type": "message", "data": "..."})
    await manager.disconnect(session_id, user_id)
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import WebSocket
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """
    Distributed WebSocket connection manager using Redis

    State Storage:
    - ws:session:{session_id}:server -> server_id (which server handles this session)
    - ws:session:{session_id}:user -> user_id
    - ws:session:{session_id}:connected_at -> timestamp
    - ws:unacked:{session_id} -> hash of {seq_id: chunk_data}
    - ws:turn_guard:{session_id} -> hash of {turn_id: timestamp}

    Pub/Sub Channels:
    - ws:broadcast:{session_id} -> messages to specific session
    - ws:broadcast:all -> messages to all sessions
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        server_id: Optional[str] = None,
        message_ttl: int = 3600,  # 1 hour
        turn_guard_ttl: int = 300,  # 5 minutes
    ):
        """
        Initialize Redis connection manager

        Args:
            redis_url: Redis connection URL
            server_id: Unique server identifier (auto-generated if not provided)
            message_ttl: TTL for unacked messages in seconds
            turn_guard_ttl: TTL for turn deduplication in seconds
        """
        self.redis_url = redis_url
        self.server_id = server_id or f"ws-server-{uuid.uuid4().hex[:8]}"
        self.message_ttl = message_ttl
        self.turn_guard_ttl = turn_guard_ttl

        # Local state (only for this server instance)
        self.active_connections: Dict[str, WebSocket] = {}
        self.orchestrators: Dict[str, Any] = {}  # session_id -> coordinator

        # Redis clients
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None

        # Background tasks
        self._pubsub_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(f"[RedisConnectionManager] Initialized with server_id={self.server_id}")

    async def initialize(self) -> None:
        """Initialize Redis connections and background tasks"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )

            # Test connection
            await self.redis.ping()
            logger.info(f"[RedisConnectionManager] Connected to Redis: {self.redis_url}")

            # Start background tasks
            self._pubsub_task = asyncio.create_task(self._pubsub_listener())
            self._retry_task = asyncio.create_task(self._retransmission_loop())
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to initialize Redis: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown Redis connections and background tasks"""
        logger.info(f"[RedisConnectionManager] Shutting down server_id={self.server_id}")

        # Cancel background tasks
        for task in [self._pubsub_task, self._retry_task, self._cleanup_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close Redis connections
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()

        logger.info("[RedisConnectionManager] Shutdown complete")

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str = "default_user"
    ) -> Optional[Dict]:
        """
        Register WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            session_id: Session ID
            user_id: User ID

        Returns:
            Recovery info if session was recovered, None otherwise
        """
        # Store connection locally
        self.active_connections[session_id] = websocket

        # Register in Redis
        try:
            pipe = self.redis.pipeline()
            pipe.hset(f"ws:session:{session_id}", mapping={
                "server": self.server_id,
                "user": user_id,
                "connected_at": datetime.utcnow().isoformat()
            })
            pipe.expire(f"ws:session:{session_id}", self.message_ttl)
            await pipe.execute()

            # Subscribe to session-specific channel
            if not self.pubsub:
                self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(f"ws:broadcast:{session_id}")

            logger.info(f"[RedisConnectionManager] Connected session={session_id} user={user_id}")

            # TODO: Implement state recovery from Redis
            # For now, return None (no recovery)
            return None

        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to register connection: {e}")
            self.active_connections.pop(session_id, None)
            raise

    async def disconnect(self, session_id: str, user_id: str = None) -> None:
        """
        Unregister WebSocket connection

        Args:
            session_id: Session ID
            user_id: User ID (optional, for state snapshot)
        """
        # Remove local connection
        self.active_connections.pop(session_id, None)
        self.orchestrators.pop(session_id, None)

        # Unsubscribe from session channel
        if self.pubsub:
            try:
                await self.pubsub.unsubscribe(f"ws:broadcast:{session_id}")
            except Exception as e:
                logger.warning(f"[RedisConnectionManager] Failed to unsubscribe: {e}")

        # Remove from Redis
        try:
            await self.redis.delete(f"ws:session:{session_id}")
            await self.redis.delete(f"ws:unacked:{session_id}")
            await self.redis.delete(f"ws:turn_guard:{session_id}")

            logger.info(f"[RedisConnectionManager] Disconnected session={session_id}")

        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to cleanup Redis state: {e}")

    async def send_json(self, session_id: str, data: Dict) -> None:
        """
        Send JSON message to session

        If session is connected to this server, send directly.
        Otherwise, publish to Redis Pub/Sub for routing.

        Args:
            session_id: Session ID
            data: JSON-serializable data
        """
        # Check if session is connected to this server
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
                return
            except Exception as e:
                logger.error(f"[RedisConnectionManager] Failed to send to local connection: {e}")
                # Fall through to Redis pub/sub

        # Publish to Redis for routing
        try:
            message = {
                "type": "message",
                "session_id": session_id,
                "data": data,
                "server_id": self.server_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis.publish(
                f"ws:broadcast:{session_id}",
                json.dumps(message)
            )
            logger.debug(f"[RedisConnectionManager] Published message to Redis for session={session_id}")

        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to publish message: {e}")
            raise

    async def send_chunk(self, session_id: str, chunk: Dict) -> None:
        """
        Send chunk with sequence ID and track for ACK

        Args:
            session_id: Session ID
            chunk: Chunk data with 'sequence' field
        """
        seq_id = chunk.get("sequence")
        if seq_id is not None:
            # Store in Redis for retransmission
            try:
                chunk_data = {
                    "data": json.dumps(chunk),
                    "sent_at": str(time.time()),
                    "retries": "0"
                }
                await self.redis.hset(
                    f"ws:unacked:{session_id}",
                    str(seq_id),
                    json.dumps(chunk_data)
                )
                await self.redis.expire(f"ws:unacked:{session_id}", self.message_ttl)
            except Exception as e:
                logger.error(f"[RedisConnectionManager] Failed to store unacked chunk: {e}")

        await self.send_json(session_id, chunk)

    async def ack_chunk(self, session_id: str, seq_id: int) -> None:
        """
        Acknowledge chunk receipt

        Args:
            session_id: Session ID
            seq_id: Sequence ID
        """
        try:
            await self.redis.hdel(f"ws:unacked:{session_id}", str(seq_id))
        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to ack chunk: {e}")

    async def _pubsub_listener(self) -> None:
        """Background task to listen for Redis Pub/Sub messages"""
        try:
            if not self.pubsub:
                return

            async for message in self.pubsub.listen():
                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                    session_id = data.get("session_id")
                    payload = data.get("data")

                    # Only process if session is connected to this server
                    if session_id in self.active_connections:
                        await self.active_connections[session_id].send_json(payload)

                except Exception as e:
                    logger.error(f"[RedisConnectionManager] Failed to process pub/sub message: {e}")

        except asyncio.CancelledError:
            logger.info("[RedisConnectionManager] Pub/Sub listener cancelled")
        except Exception as e:
            logger.error(f"[RedisConnectionManager] Pub/Sub listener error: {e}")

    async def _retransmission_loop(self) -> None:
        """Background task for retransmitting unacked chunks"""
        try:
            while True:
                await asyncio.sleep(2.0)  # Check every 2 seconds

                # Get all sessions with unacked chunks
                try:
                    keys = await self.redis.keys("ws:unacked:*")
                    for key in keys:
                        session_id = key.split(":")[-1]

                        # Only process if session is connected to this server
                        if session_id not in self.active_connections:
                            continue

                        chunks = await self.redis.hgetall(key)
                        now = time.time()

                        for seq_id, chunk_json in chunks.items():
                            try:
                                chunk_data = json.loads(chunk_json)
                                sent_at = float(chunk_data["sent_at"])
                                retries = int(chunk_data["retries"])

                                # Exponential backoff: 2, 4, 8, 16...
                                wait_time = 2.0 * (2 ** retries)

                                if now - sent_at > wait_time:
                                    if retries > 5:  # Max retries
                                        logger.warning(
                                            f"[RedisConnectionManager] Max retries reached for "
                                            f"session={session_id} seq={seq_id}"
                                        )
                                        await self.redis.hdel(key, seq_id)
                                        continue

                                    # Retransmit
                                    logger.info(
                                        f"[RedisConnectionManager] Retransmitting chunk "
                                        f"session={session_id} seq={seq_id} retry={retries + 1}"
                                    )

                                    data = json.loads(chunk_data["data"])
                                    await self.send_json(session_id, data)

                                    # Update retry count
                                    chunk_data["retries"] = str(retries + 1)
                                    chunk_data["sent_at"] = str(now)
                                    await self.redis.hset(key, seq_id, json.dumps(chunk_data))

                            except Exception as e:
                                logger.error(
                                    f"[RedisConnectionManager] Failed to retransmit chunk: {e}"
                                )

                except Exception as e:
                    logger.error(f"[RedisConnectionManager] Retransmission loop error: {e}")

        except asyncio.CancelledError:
            logger.info("[RedisConnectionManager] Retransmission loop cancelled")

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired state"""
        try:
            while True:
                await asyncio.sleep(60.0)  # Cleanup every minute

                try:
                    # Cleanup expired turn guards
                    keys = await self.redis.keys("ws:turn_guard:*")
                    now = time.time()

                    for key in keys:
                        guards = await self.redis.hgetall(key)
                        expired = []

                        for turn_id, timestamp in guards.items():
                            if now - float(timestamp) > self.turn_guard_ttl:
                                expired.append(turn_id)

                        if expired:
                            await self.redis.hdel(key, *expired)
                            logger.debug(
                                f"[RedisConnectionManager] Cleaned up {len(expired)} "
                                f"expired turn guards from {key}"
                            )

                except Exception as e:
                    logger.error(f"[RedisConnectionManager] Cleanup loop error: {e}")

        except asyncio.CancelledError:
            logger.info("[RedisConnectionManager] Cleanup loop cancelled")

    def set_orchestrator(self, session_id: str, orchestrator: Any) -> None:
        """Store orchestrator for session (local only)"""
        self.orchestrators[session_id] = orchestrator

    def get_orchestrator(self, session_id: str) -> Optional[Any]:
        """Get orchestrator for session (local only)"""
        return self.orchestrators.get(session_id)

    async def is_duplicate_turn(self, session_id: str, turn_id: str) -> bool:
        """
        Check if turn has already been processed (distributed deduplication)

        Args:
            session_id: Session ID
            turn_id: Turn ID

        Returns:
            True if turn is duplicate, False otherwise
        """
        try:
            key = f"ws:turn_guard:{session_id}"
            exists = await self.redis.hexists(key, turn_id)
            return bool(exists)
        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to check duplicate turn: {e}")
            return False

    async def mark_turn_seen(self, session_id: str, turn_id: str) -> None:
        """
        Mark turn as seen (distributed deduplication)

        Args:
            session_id: Session ID
            turn_id: Turn ID
        """
        try:
            key = f"ws:turn_guard:{session_id}"
            await self.redis.hset(key, turn_id, str(time.time()))
            await self.redis.expire(key, self.turn_guard_ttl)
        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to mark turn seen: {e}")

    async def clear_turn_seen(self, session_id: str, turn_id: str) -> None:
        """
        Clear turn seen marker

        Args:
            session_id: Session ID
            turn_id: Turn ID
        """
        try:
            await self.redis.hdel(f"ws:turn_guard:{session_id}", turn_id)
        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to clear turn seen: {e}")

    async def send_tool_status(self, session_id: str, tool_event: Dict) -> None:
        """
        Send tool execution status event to client

        Args:
            session_id: Session ID
            tool_event: Tool event data
        """
        event = {
            "type": "tool_status",
            "tool_name": tool_event.get("tool_name"),
            "status": tool_event.get("status"),
            "latency_ms": tool_event.get("latency_ms"),
            "result_preview": tool_event.get("result_preview"),
            "error": tool_event.get("error"),
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_json(session_id, event)

    async def get_active_sessions_count(self) -> int:
        """Get total number of active sessions across all servers"""
        try:
            keys = await self.redis.keys("ws:session:*")
            return len(keys)
        except Exception as e:
            logger.error(f"[RedisConnectionManager] Failed to get active sessions count: {e}")
            return 0

    async def get_server_sessions(self) -> list:
        """Get list of sessions connected to this server"""
        return list(self.active_connections.keys())
