import json
from typing import Any, Dict, Optional

import core.redis as redis_module


class ReplayEngine:
    def __init__(self) -> None:
        self._snapshot_prefix = "snapshot:sales_state:"
        self._stream_key = "stream:sales_state"

    async def save_snapshot(self, session_id: str, state: Dict[str, Any]) -> None:
        redis = await redis_module.get_redis()
        key = f"{self._snapshot_prefix}{session_id}"
        await redis.set(key, json.dumps(state, ensure_ascii=False))

    async def load_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        redis = await redis_module.get_redis()
        key = f"{self._snapshot_prefix}{session_id}"
        raw = await redis.get(key)
        if not raw:
            return None
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def replay(self, session_id: str) -> Dict[str, Any]:
        redis = await redis_module.get_redis()
        snapshot = await self.load_snapshot(session_id)
        base_state: Dict[str, Any] = snapshot or {}
        base_turn = int(base_state.get("turn_id", 0) or 0)

        entries = await redis.xrange(self._stream_key)
        best_by_turn: Dict[int, Dict[str, Any]] = {}

        for _msg_id, fields in entries:
            raw = fields.get("data") if isinstance(fields, dict) else None
            if not raw:
                continue
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8", errors="ignore")
            try:
                event = json.loads(raw)
            except Exception:
                continue
            if event.get("session_id") != session_id:
                continue
            state = event.get("state") or {}
            turn_id = int(event.get("turn_id") or state.get("turn_id") or 0)
            if turn_id <= 0:
                continue
            if turn_id < base_turn:
                continue
            best_by_turn[turn_id] = state

        if not best_by_turn:
            return base_state

        latest_turn = max(best_by_turn.keys())
        return best_by_turn[latest_turn]
