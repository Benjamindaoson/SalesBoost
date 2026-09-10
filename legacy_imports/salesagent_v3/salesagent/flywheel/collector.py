"""Preference Pair Collector and Redis Streams Consumer."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog

from salesagent.core.constants import REDIS_STREAM_FSM_EVENTS, REDIS_STREAM_GUARD_EVENTS, REDIS_STREAM_FLYWHEEL
from salesagent.models.db_models import PreferencePair

log = structlog.get_logger()


class PreferencePairCollector:
    def __init__(self, db: Any) -> None:
        self.db = db

    async def collect(
        self,
        session_id: str,
        turn_index: int,
        user_message: str,
        chosen_response: str,
        rejected_response: str,
        reward_scores: dict[str, float],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a preference pair for DPO training."""
        pair = PreferencePair(
            session_id=session_id,
            turn_index=turn_index,
            user_message=user_message,
            chosen_response=chosen_response,
            rejected_response=rejected_response,
            reward_scores=reward_scores,
            metadata_=metadata or {},
        )
        self.db.add(pair)
        await self.db.commit()
        await self.db.refresh(pair)
        log.debug("Preference pair collected", session_id=session_id, pair_id=pair.id)
        return pair.id


class StreamsConsumer:
    """
    Background consumer for Redis Streams events.
    Consumes FSM transitions, Guard events, and Flywheel data for analytics and training.
    """

    def __init__(self, redis: Any, db: Any) -> None:
        self.redis = redis
        self.db = db
        self._running = False

    async def start(self) -> None:
        """Start consuming all streams in parallel."""
        self._running = True
        await asyncio.gather(
            self._consume_fsm_events(),
            self._consume_guard_events(),
            self._consume_flywheel_events(),
        )

    async def stop(self) -> None:
        """Stop all consumers gracefully."""
        self._running = False

    async def _consume_fsm_events(self) -> None:
        """Consume FSM transition events for analytics."""
        consumer_group = "flywheel_fsm_consumer"
        consumer_name = "worker_1"

        # Create consumer group if not exists
        try:
            await self.redis.xgroup_create(REDIS_STREAM_FSM_EVENTS, consumer_group, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists

        log.info("FSM events consumer started", stream=REDIS_STREAM_FSM_EVENTS)

        while self._running:
            try:
                # Read from stream with blocking
                events = await self.redis.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {REDIS_STREAM_FSM_EVENTS: ">"},
                    count=10,
                    block=5000,  # 5 seconds timeout
                )

                for stream_name, messages in events:
                    for message_id, data in messages:
                        await self._process_fsm_event(data)
                        # Acknowledge message
                        await self.redis.xack(REDIS_STREAM_FSM_EVENTS, consumer_group, message_id)

            except Exception as exc:
                log.error("FSM consumer error", error=str(exc))
                await asyncio.sleep(1)

    async def _consume_guard_events(self) -> None:
        """Consume Guard interception events for compliance monitoring."""
        consumer_group = "flywheel_guard_consumer"
        consumer_name = "worker_1"

        try:
            await self.redis.xgroup_create(REDIS_STREAM_GUARD_EVENTS, consumer_group, id="0", mkstream=True)
        except Exception:
            pass

        log.info("Guard events consumer started", stream=REDIS_STREAM_GUARD_EVENTS)

        while self._running:
            try:
                events = await self.redis.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {REDIS_STREAM_GUARD_EVENTS: ">"},
                    count=10,
                    block=5000,
                )

                for stream_name, messages in events:
                    for message_id, data in messages:
                        await self._process_guard_event(data)
                        await self.redis.xack(REDIS_STREAM_GUARD_EVENTS, consumer_group, message_id)

            except Exception as exc:
                log.error("Guard consumer error", error=str(exc))
                await asyncio.sleep(1)

    async def _consume_flywheel_events(self) -> None:
        """Consume Flywheel training data events."""
        consumer_group = "flywheel_training_consumer"
        consumer_name = "worker_1"

        try:
            await self.redis.xgroup_create(REDIS_STREAM_FLYWHEEL, consumer_group, id="0", mkstream=True)
        except Exception:
            pass

        log.info("Flywheel events consumer started", stream=REDIS_STREAM_FLYWHEEL)

        while self._running:
            try:
                events = await self.redis.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {REDIS_STREAM_FLYWHEEL: ">"},
                    count=10,
                    block=5000,
                )

                for stream_name, messages in events:
                    for message_id, data in messages:
                        await self._process_flywheel_event(data)
                        await self.redis.xack(REDIS_STREAM_FLYWHEEL, consumer_group, message_id)

            except Exception as exc:
                log.error("Flywheel consumer error", error=str(exc))
                await asyncio.sleep(1)

    async def _process_fsm_event(self, data: dict[str, str]) -> None:
        """Process FSM transition event."""
        try:
            event = json.loads(data.get("event", "{}"))
            session_id = data.get("session_id")
            log.debug(
                "FSM event processed",
                session_id=session_id,
                from_stage=event.get("from"),
                to_stage=event.get("to"),
                signal=event.get("signal"),
            )
            # TODO: Store in analytics DB or trigger downstream actions
        except Exception as exc:
            log.warning("Failed to process FSM event", error=str(exc))

    async def _process_guard_event(self, data: dict[str, str]) -> None:
        """Process Guard interception event."""
        try:
            event = json.loads(data.get("event", "{}"))
            log.debug(
                "Guard event processed",
                session_id=event.get("session_id"),
                risk_type=event.get("risk_type"),
            )
            # TODO: Store compliance violations for audit
        except Exception as exc:
            log.warning("Failed to process Guard event", error=str(exc))

    async def _process_flywheel_event(self, data: dict[str, str]) -> None:
        """Process Flywheel training data event."""
        try:
            event = json.loads(data.get("event", "{}"))
            log.debug("Flywheel event processed", session_id=event.get("session_id"))
            # TODO: Aggregate training data for APO engine
        except Exception as exc:
            log.warning("Failed to process Flywheel event", error=str(exc))
