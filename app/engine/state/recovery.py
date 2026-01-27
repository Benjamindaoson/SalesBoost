"""In-memory state recovery service stub."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RecoverySnapshot:
    session_id: str
    user_id: str
    orchestrator: object


class StateSnapshotService:
    def __init__(self) -> None:
        self._snapshots: Dict[str, RecoverySnapshot] = {}

    async def delete_snapshot(self, session_id: str) -> bool:
        return self._snapshots.pop(session_id, None) is not None


class StateRecoveryService:
    def __init__(self) -> None:
        self._snapshots: Dict[str, RecoverySnapshot] = {}
        self.state_snapshot_service = StateSnapshotService()

    async def initialize(self) -> None:
        return None

    async def create_recovery_checkpoint(self, session_id: str, user_id: str, agent_type: str, orchestrator: object) -> None:
        snapshot = RecoverySnapshot(session_id=session_id, user_id=user_id, orchestrator=orchestrator)
        self._snapshots[session_id] = snapshot

    async def recover_session_state(self, session_id: str, user_id: str) -> Optional[dict]:
        snapshot = self._snapshots.get(session_id)
        if snapshot and snapshot.user_id == user_id:
            return {"orchestrator": snapshot.orchestrator}
        return None

    async def list_recoverable_sessions(self, user_id: str) -> list:
        return [s.session_id for s in self._snapshots.values() if s.user_id == user_id]


state_recovery_service = StateRecoveryService()
