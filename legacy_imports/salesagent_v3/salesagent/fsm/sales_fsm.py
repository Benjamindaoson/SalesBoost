"""SalesFSM — deterministic sales funnel state machine with PostgreSQL persistence."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from salesagent.core.constants import (
    REDIS_STREAM_FSM_EVENTS,
    SaleStage,
    StageSignal,
)
from salesagent.fsm.states import STAGE_CONFIGS, StageConfig
from salesagent.fsm.transitions import can_transition, get_next_stage
from salesagent.utils.exceptions import InvalidTransitionError, SessionNotFoundError
from salesagent.observability.metrics import fsm_transitions_total, fsm_current_stage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from redis.asyncio import Redis

log = structlog.get_logger()


class SalesFSM:
    """
    Deterministic sales funnel state machine.

    - Zero LLM dependency — all transitions are rule-based.
    - Persists stage to PostgreSQL via async SQLAlchemy session.
    - Emits Redis Streams events on every transition for the data flywheel.
    """

    def __init__(
        self,
        session_id: str,
        current_stage: SaleStage = SaleStage.ICEBREAK,
        stage_history: list[dict[str, Any]] | None = None,
    ) -> None:
        self.session_id = session_id
        self.current_stage = current_stage
        self._history: list[dict[str, Any]] = stage_history or []

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def stage_config(self) -> StageConfig:
        return STAGE_CONFIGS[self.current_stage]

    @property
    def history(self) -> list[dict[str, Any]]:
        return self._history

    # ── Transitions ───────────────────────────────────────────────────────────

    async def advance(
        self,
        signal: StageSignal,
        db: AsyncSession | None = None,
        redis: Redis | None = None,
    ) -> SaleStage:
        """
        Attempt to advance the FSM with the given signal.
        Returns the new stage (which may be unchanged if signal == STAY).

        Args:
            signal: Structured signal from the Reasoning Chain.
            db: AsyncSession (optional) — if provided, persists to PostgreSQL.
            redis: Redis client (optional) — if provided, emits stream event.
        """
        if signal == StageSignal.STAY:
            log.debug("FSM: STAY signal, no transition", stage=self.current_stage.value)
            return self.current_stage

        if not can_transition(self.current_stage, signal):
            raise InvalidTransitionError(
                message=f"Cannot transition from {self.current_stage.value} with signal {signal.value}",
            )

        previous_stage = self.current_stage
        next_stage = get_next_stage(self.current_stage, signal)

        # Record history entry
        history_entry: dict[str, Any] = {
            "from": previous_stage.value,
            "to": next_stage.value,
            "signal": signal.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(history_entry)
        self.current_stage = next_stage

        # Update metrics
        fsm_transitions_total.labels(
            from_stage=previous_stage.value,
            to_stage=next_stage.value,
            signal=signal.value,
        ).inc()
        fsm_current_stage.labels(stage=next_stage.value).inc()

        log.info(
            "FSM transition",
            session_id=self.session_id,
            from_stage=previous_stage.value,
            to_stage=next_stage.value,
            signal=signal.value,
        )

        # Persist to DB
        if db is not None:
            await self._persist(db)

        # Emit Redis Streams event
        if redis is not None:
            await self._emit_event(redis, history_entry)

        return next_stage

    async def rollback(
        self,
        target_stage: SaleStage,
        db: AsyncSession | None = None,
        redis: Redis | None = None,
    ) -> SaleStage:
        """Explicitly roll back to a previous stage (e.g., PROPOSAL → DISCOVERY on new need)."""
        config = STAGE_CONFIGS[self.current_stage]
        if target_stage not in config.allowed_back_transitions:
            raise InvalidTransitionError(
                message=f"Rollback from {self.current_stage.value} to {target_stage.value} not allowed",
            )

        previous_stage = self.current_stage
        history_entry: dict[str, Any] = {
            "from": previous_stage.value,
            "to": target_stage.value,
            "signal": "rollback",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._history.append(history_entry)
        self.current_stage = target_stage

        log.info(
            "FSM rollback",
            session_id=self.session_id,
            from_stage=previous_stage.value,
            to_stage=target_stage.value,
        )

        if db is not None:
            await self._persist(db)
        if redis is not None:
            await self._emit_event(redis, history_entry)

        return target_stage

    # ── Persistence ───────────────────────────────────────────────────────────

    async def _persist(self, db: AsyncSession) -> None:
        """Update the sessions table with current stage + history."""
        from sqlalchemy import update
        from salesagent.models.db_models import Session as SessionModel

        await db.execute(
            update(SessionModel)
            .where(SessionModel.id == self.session_id)
            .values(
                current_stage=self.current_stage.value,
                stage_history=self._history,
            )
        )
        await db.commit()

    async def _emit_event(self, redis: Redis, entry: dict[str, Any]) -> None:
        """Emit FSM transition event to Redis Streams for the data flywheel."""
        try:
            await redis.xadd(
                REDIS_STREAM_FSM_EVENTS,
                {
                    "session_id": self.session_id,
                    "event": json.dumps(entry),
                },
                maxlen=10_000,
                approximate=True,
            )
        except Exception as exc:
            log.warning("Failed to emit FSM event to Redis", error=str(exc))

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    async def from_session(cls, session_id: str, db: AsyncSession) -> SalesFSM:
        """Load FSM state from PostgreSQL session record."""
        from sqlalchemy import select
        from salesagent.models.db_models import Session as SessionModel

        result = await db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        session_row = result.scalar_one_or_none()
        if session_row is None:
            raise SessionNotFoundError(message=f"Session {session_id} not found")

        return cls(
            session_id=session_id,
            current_stage=SaleStage(session_row.current_stage),
            stage_history=session_row.stage_history or [],
        )
