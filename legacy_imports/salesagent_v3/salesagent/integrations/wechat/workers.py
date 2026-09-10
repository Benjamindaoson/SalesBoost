"""Background workers for processing WeChat messages.

This module contains worker processes that:
1. Consume inbound messages and trigger AI chat
2. Consume outbound messages and send to WeChat
"""
from __future__ import annotations

import asyncio
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from salesagent.integrations.message_queue import MessageQueue
from salesagent.integrations.wechat_work import get_wechat_client
from salesagent.core.settings import settings
from salesagent.main import AsyncSessionLocal, get_redis

log = structlog.get_logger()


class InboundWorker:
    """Worker that consumes inbound messages and triggers AI chat."""

    def __init__(self, worker_id: str = "worker_1"):
        self.worker_id = worker_id
        self.running = False

    async def start(self) -> None:
        """Start the inbound worker."""
        self.running = True
        redis = await get_redis()
        queue = MessageQueue(redis)

        # Initialize consumer groups
        await queue.initialize()

        log.info("Starting inbound worker", worker_id=self.worker_id)

        # Start consuming
        await queue.consume_inbound(
            consumer_name=self.worker_id,
            callback=self._process_message,
        )

    async def stop(self) -> None:
        """Stop the inbound worker."""
        self.running = False
        log.info("Stopping inbound worker", worker_id=self.worker_id)

    async def _process_message(
        self,
        user_id: str,
        content: str,
        session_id: str | None,
        metadata: Any,
    ) -> None:
        """Process inbound message by triggering AI chat.

        Args:
            user_id: WeChat user ID
            content: Message content
            session_id: Optional session ID
            metadata: Optional metadata
        """
        log.info(
            "Processing inbound message",
            user_id=user_id,
            session_id=session_id,
            content_preview=content[:50],
        )

        try:
            async with AsyncSessionLocal() as db:
                # Import here to avoid circular dependency
                from salesagent.api.chat_helper import process_chat_message

                # Get or create session
                if not session_id:
                    from salesagent.models.db_models import Session as SessionModel

                    # Create new session
                    session = SessionModel(
                        user_id=user_id,
                        channel="wechat",
                        customer_profile={"wechat_user_id": user_id},
                    )
                    db.add(session)
                    await db.commit()
                    await db.refresh(session)
                    session_id = session.id
                    log.info("Created new session", session_id=session_id)

                # Process message through AI engine
                redis = await get_redis()
                response_text = await process_chat_message(
                    session_id=session_id,
                    user_message=content,
                    db=db,
                    redis=redis,
                )

                # Schedule outbound message
                queue = MessageQueue(redis)
                await queue.schedule_outbound(
                    user_id=user_id,
                    content=response_text,
                    session_id=session_id,
                )

                log.info(
                    "Scheduled AI response",
                    session_id=session_id,
                    response_preview=response_text[:50],
                )

        except Exception as e:
            log.error(
                "Failed to process inbound message",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise


class OutboundWorker:
    """Worker that consumes outbound messages and sends to WeChat."""

    def __init__(self, worker_id: str = "sender_1"):
        self.worker_id = worker_id
        self.running = False

    async def start(self) -> None:
        """Start the outbound worker."""
        self.running = True
        redis = await get_redis()
        queue = MessageQueue(redis)

        # Initialize consumer groups
        await queue.initialize()

        log.info("Starting outbound worker", worker_id=self.worker_id)

        # Start consuming
        await queue.consume_outbound(
            consumer_name=self.worker_id,
            callback=self._send_message,
        )

    async def stop(self) -> None:
        """Stop the outbound worker."""
        self.running = False
        log.info("Stopping outbound worker", worker_id=self.worker_id)

    async def _send_message(
        self,
        user_id: str,
        content: str,
        session_id: str,
    ) -> None:
        """Send message to WeChat user.

        Args:
            user_id: WeChat user ID
            content: Message content
            session_id: Session ID
        """
        log.info(
            "Sending outbound message",
            user_id=user_id,
            session_id=session_id,
            content_preview=content[:50],
        )

        try:
            # Check if AI is paused for this session
            redis = await get_redis()
            is_paused = await redis.get(f"session:{session_id}:ai_paused")
            if is_paused:
                log.info(
                    "AI paused, skipping message send",
                    session_id=session_id,
                )
                return

            # Send message via WeChat API
            client = get_wechat_client()
            result = await client.send_text_message(user_id, content)

            log.info(
                "Sent outbound message",
                user_id=user_id,
                session_id=session_id,
                msgid=result.get("msgid"),
            )

        except Exception as e:
            log.error(
                "Failed to send outbound message",
                user_id=user_id,
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise


async def start_workers() -> tuple[InboundWorker, OutboundWorker]:
    """Start both inbound and outbound workers.

    Returns:
        Tuple of (inbound_worker, outbound_worker)
    """
    inbound = InboundWorker(worker_id="inbound_1")
    outbound = OutboundWorker(worker_id="outbound_1")

    # Start workers in background tasks
    asyncio.create_task(inbound.start())
    asyncio.create_task(outbound.start())

    log.info("Started WeChat workers")
    return inbound, outbound


async def stop_workers(
    inbound: InboundWorker,
    outbound: OutboundWorker,
) -> None:
    """Stop both workers.

    Args:
        inbound: Inbound worker instance
        outbound: Outbound worker instance
    """
    await inbound.stop()
    await outbound.stop()
    log.info("Stopped WeChat workers")
