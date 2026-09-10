"""PostgreSQL-based LangGraph Checkpointer."""
from __future__ import annotations

import json
import pickle
from typing import Any, Optional, Sequence

import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


class PostgresCheckpointer(BaseCheckpointSaver):
    """
    PostgreSQL-based checkpointer for LangGraph.

    Stores checkpoint data in a dedicated table, enabling:
    - HITL state persistence across service restarts
    - Horizontal scaling (multiple workers share checkpoint state)
    - Audit trail of all state transitions
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__()
        self.db = db

    async def aget(
        self,
        config: dict[str, Any],
    ) -> Optional[Checkpoint]:
        """Load checkpoint from PostgreSQL."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        try:
            result = await self.db.execute(
                text("""
                    SELECT checkpoint_data, metadata
                    FROM langgraph_checkpoints
                    WHERE thread_id = :thread_id
                    ORDER BY checkpoint_id DESC
                    LIMIT 1
                """),
                {"thread_id": thread_id}
            )
            row = result.fetchone()
            if not row:
                return None

            checkpoint_data = pickle.loads(row[0])
            return checkpoint_data

        except Exception as exc:
            log.error("Failed to load checkpoint", error=str(exc), thread_id=thread_id)
            return None

    async def aput(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> dict[str, Any]:
        """Save checkpoint to PostgreSQL."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("thread_id required in config")

        try:
            checkpoint_data = pickle.dumps(checkpoint)
            metadata_json = json.dumps(metadata)

            await self.db.execute(
                text("""
                    INSERT INTO langgraph_checkpoints (thread_id, checkpoint_data, metadata)
                    VALUES (:thread_id, :checkpoint_data, :metadata)
                    ON CONFLICT (thread_id)
                    DO UPDATE SET
                        checkpoint_data = EXCLUDED.checkpoint_data,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """),
                {
                    "thread_id": thread_id,
                    "checkpoint_data": checkpoint_data,
                    "metadata": metadata_json,
                }
            )
            await self.db.commit()

            log.debug("Checkpoint saved", thread_id=thread_id)
            return config

        except Exception as exc:
            log.error("Failed to save checkpoint", error=str(exc), thread_id=thread_id)
            await self.db.rollback()
            raise

    async def alist(
        self,
        config: dict[str, Any],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> list[Checkpoint]:
        """List checkpoints (for debugging/audit)."""
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return []

        try:
            query = """
                SELECT checkpoint_data
                FROM langgraph_checkpoints
                WHERE thread_id = :thread_id
                ORDER BY checkpoint_id DESC
            """
            if limit:
                query += f" LIMIT {limit}"

            result = await self.db.execute(
                text(query),
                {"thread_id": thread_id}
            )
            rows = result.fetchall()
            return [pickle.loads(row[0]) for row in rows]

        except Exception as exc:
            log.error("Failed to list checkpoints", error=str(exc))
            return []

    def get(self, config: dict[str, Any]) -> Optional[Checkpoint]:
        """Sync version (not used in async context)."""
        raise NotImplementedError("Use aget() for async operations")

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
    ) -> dict[str, Any]:
        """Sync version (not used in async context)."""
        raise NotImplementedError("Use aput() for async operations")

    def list(
        self,
        config: dict[str, Any],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> list[Checkpoint]:
        """Sync version (not used in async context)."""
        raise NotImplementedError("Use alist() for async operations")
