"""State recovery service with persistent snapshots."""
from __future__ import annotations

import logging
from typing import Optional

from .snapshot import state_snapshot_service

logger = logging.getLogger(__name__)

class StateRecoveryService:
    def __init__(self) -> None:
        self.state_snapshot_service = state_snapshot_service

    async def initialize(self) -> None:
        """Initialize any recovery resources."""
        return None

    async def create_recovery_checkpoint(
        self, 
        session_id: str, 
        user_id: str, 
        current_stage: str, 
        context: dict
    ) -> str:
        """Create a checkpoint for session recovery."""
        snapshot_id = f"checkpoint_{session_id}"
        await self.state_snapshot_service.create_snapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            user_id=user_id,
            current_stage=current_stage,
            context=context
        )
        return snapshot_id

    async def recover_session_state(self, session_id: str, user_id: str) -> Optional[dict]:
        """Recover the state of a session from the latest checkpoint."""
        snapshot_id = f"checkpoint_{session_id}"
        snapshot = await self.state_snapshot_service.get_snapshot(snapshot_id)
        
        if snapshot and snapshot.user_id == user_id:
            logger.info(f"Recovered session state for: {session_id}")
            return {
                "current_stage": snapshot.current_stage,
                "context": snapshot.context
            }
        return None

state_recovery_service = StateRecoveryService()
