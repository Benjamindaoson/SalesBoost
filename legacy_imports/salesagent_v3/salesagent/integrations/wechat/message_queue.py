"""Message queue management using Redis Streams.

This module implements a dual-queue architecture:
- Inbound queue: Customer messages → AI engine
- Outbound queue: AI responses → Customer (with delay scheduling)
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.core.settings import settings

log = structlog.get_logger()


class MessageQueue:
    """Message queue manager using Redis Streams."""

    INBOUND_STREAM = "stream:wechat_inbound"  # Customer → AI
    OUTBOUND_STREAM = "stream:wechat_outbound"  # AI → Customer
    INBOUND_GROUP = "ai_consumer_group"
    OUTBOUND_GROUP = "sender_group"

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def initialize(self) -> None:
        """Initialize consumer groups."""
        try:
            # Create inbound consumer group
            await self.redis.xgroup_create(
                self.INBOUND_STREAM,
                self.INBOUND_GROUP,
                id="0",
                mkstream=True,
            )
            log.info("Created inbound consumer group", stream=self.INBOUND_STREAM)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            log.debug("Inbound consumer group already exists")

        try:
            # Create outbound consumer group
            await self.redis.xgroup_create(
                self.OUTBOUND_STREAM,
                self.OUTBOUND_GROUP,
                id="0",
                mkstream=True,
            )
            log.info("Created outbound consumer group", stream=self.OUTBOUND_STREAM)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            log.debug("Outbound consumer group already exists")

    async def push_inbound(
        self,
        user_id: str,
        content: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Push customer message to inbound queue.

        Args:
            user_id: WeChat user ID
            content: Message content
            session_id: Optional session ID
            metadata: Optional metadata

        Returns:
            Message ID
        """
        data = {
            "user_id": user_id,
            "content": content,
            "timestamp": time.time(),
        }
        if session_id:
            data["session_id"] = session_id
        if metadata:
            data["metadata"] = str(metadata)

        msg_id = await self.redis.xadd(self.INBOUND_STREAM, data)
        log.info(
            "Pushed inbound message",
            msg_id=msg_id,
            user_id=user_id,
            session_id=session_id,
        )
        return msg_id

    async def schedule_outbound(
        self,
        user_id: str,
        content: str,
        session_id: str,
        delay_seconds: int | None = None,
    ) -> str:
        """Schedule outbound message with delay.

        Args:
            user_id: WeChat user ID
            content: Message content
            session_id: Session ID
            delay_seconds: Delay in seconds (random if None)

        Returns:
            Message ID
        """
        if delay_seconds is None:
            # Random delay between configured min/max
            delay_seconds = random.randint(
                settings.typing_sim_delay_min,
                settings.typing_sim_delay_max,
            )

        send_at = time.time() + delay_seconds

        data = {
            "user_id": user_id,
            "content": content,
            "session_id": session_id,
            "send_at": send_at,
            "scheduled_at": time.time(),
        }

        msg_id = await self.redis.xadd(self.OUTBOUND_STREAM, data)
        log.info(
            "Scheduled outbound message",
            msg_id=msg_id,
            user_id=user_id,
            session_id=session_id,
            delay_seconds=delay_seconds,
        )
        return msg_id

    async def consume_inbound(
        self,
        consumer_name: str,
        callback: Any,
        batch_size: int = 10,
        block_ms: int = 5000,
    ) -> None:
        """Consume inbound messages and trigger AI processing.

        Args:
            consumer_name: Consumer name (e.g., "ai_worker_1")
            callback: Async callback function(user_id, content, session_id, metadata)
            batch_size: Number of messages to fetch per batch
            block_ms: Block timeout in milliseconds
        """
        log.info(
            "Starting inbound consumer",
            consumer_name=consumer_name,
            stream=self.INBOUND_STREAM,
        )

        while True:
            try:
                # Read messages from stream
                messages = await self.redis.xreadgroup(
                    self.INBOUND_GROUP,
                    consumer_name,
                    {self.INBOUND_STREAM: ">"},
                    count=batch_size,
                    block=block_ms,
                )

                if not messages:
                    continue

                for stream, msg_list in messages:
                    for msg_id, data in msg_list:
                        try:
                            user_id = data.get("user_id")
                            content = data.get("content")
                            session_id = data.get("session_id")
                            metadata = data.get("metadata")

                            # Trigger callback
                            await callback(user_id, content, session_id, metadata)

                            # ACK message
                            await self.redis.xack(
                                self.INBOUND_STREAM,
                                self.INBOUND_GROUP,
                                msg_id,
                            )
                            log.debug("Processed inbound message", msg_id=msg_id)

                        except Exception as e:
                            log.error(
                                "Failed to process inbound message",
                                msg_id=msg_id,
                                error=str(e),
                                exc_info=True,
                            )
                            # Don't ACK failed messages, they'll be retried

            except asyncio.CancelledError:
                log.info("Inbound consumer cancelled", consumer_name=consumer_name)
                break
            except Exception as e:
                log.error(
                    "Error in inbound consumer",
                    consumer_name=consumer_name,
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(5)  # Back off on error

    async def consume_outbound(
        self,
        consumer_name: str,
        callback: Any,
        batch_size: int = 10,
        block_ms: int = 1000,
    ) -> None:
        """Consume outbound messages and send when time is reached.

        Args:
            consumer_name: Consumer name (e.g., "sender_1")
            callback: Async callback function(user_id, content, session_id)
            batch_size: Number of messages to fetch per batch
            block_ms: Block timeout in milliseconds
        """
        log.info(
            "Starting outbound consumer",
            consumer_name=consumer_name,
            stream=self.OUTBOUND_STREAM,
        )

        while True:
            try:
                # Read messages from stream
                messages = await self.redis.xreadgroup(
                    self.OUTBOUND_GROUP,
                    consumer_name,
                    {self.OUTBOUND_STREAM: ">"},
                    count=batch_size,
                    block=block_ms,
                )

                if not messages:
                    continue

                now = time.time()

                for stream, msg_list in messages:
                    for msg_id, data in msg_list:
                        try:
                            send_at = float(data.get("send_at", 0))

                            # Check if it's time to send
                            if now >= send_at:
                                user_id = data.get("user_id")
                                content = data.get("content")
                                session_id = data.get("session_id")

                                # Send message
                                await callback(user_id, content, session_id)

                                # ACK message
                                await self.redis.xack(
                                    self.OUTBOUND_STREAM,
                                    self.OUTBOUND_GROUP,
                                    msg_id,
                                )
                                log.debug("Sent outbound message", msg_id=msg_id)
                            else:
                                # Not time yet, will retry in next iteration
                                log.debug(
                                    "Message not ready to send",
                                    msg_id=msg_id,
                                    wait_seconds=int(send_at - now),
                                )

                        except Exception as e:
                            log.error(
                                "Failed to send outbound message",
                                msg_id=msg_id,
                                error=str(e),
                                exc_info=True,
                            )
                            # Don't ACK failed messages, they'll be retried

            except asyncio.CancelledError:
                log.info("Outbound consumer cancelled", consumer_name=consumer_name)
                break
            except Exception as e:
                log.error(
                    "Error in outbound consumer",
                    consumer_name=consumer_name,
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(5)  # Back off on error

    async def get_pending_count(self, stream: str, group: str) -> int:
        """Get number of pending messages in consumer group.

        Args:
            stream: Stream name
            group: Consumer group name

        Returns:
            Number of pending messages
        """
        info = await self.redis.xpending(stream, group)
        return info["pending"] if info else 0

    async def claim_pending_messages(
        self,
        stream: str,
        group: str,
        consumer_name: str,
        min_idle_time_ms: int = 60000,
    ) -> list[tuple[str, dict]]:
        """Claim pending messages that have been idle too long.

        Args:
            stream: Stream name
            group: Consumer group name
            consumer_name: Consumer name to claim for
            min_idle_time_ms: Minimum idle time in milliseconds

        Returns:
            List of (msg_id, data) tuples
        """
        # Get pending messages
        pending = await self.redis.xpending_range(
            stream,
            group,
            min="-",
            max="+",
            count=100,
        )

        claimed = []
        for msg_info in pending:
            msg_id = msg_info["message_id"]
            idle_time = msg_info["time_since_delivered"]

            if idle_time >= min_idle_time_ms:
                # Claim the message
                result = await self.redis.xclaim(
                    stream,
                    group,
                    consumer_name,
                    min_idle_time_ms,
                    [msg_id],
                )
                if result:
                    claimed.extend(result)
                    log.info(
                        "Claimed pending message",
                        msg_id=msg_id,
                        idle_time_ms=idle_time,
                    )

        return claimed
