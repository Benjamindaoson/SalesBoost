"""State snapshot stub."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Snapshot:
    snapshot_id: str
    session_id: str
    user_id: str
    current_stage: str
    context: dict


class StateSnapshotService:
    def __init__(self) -> None:
        self._snapshots: Dict[str, Snapshot] = {}

    async def create_snapshot(self, snapshot_id: str, session_id: str, user_id: str, current_stage: str, context: dict) -> Snapshot:
        snapshot = Snapshot(snapshot_id=snapshot_id, session_id=session_id, user_id=user_id, current_stage=current_stage, context=context)
        self._snapshots[snapshot_id] = snapshot
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        return self._snapshots.get(snapshot_id)

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        return self._snapshots.pop(snapshot_id, None) is not None


state_snapshot_service = StateSnapshotService()
