"""SalesState synchronization via Redis Streams."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

from core.redis import get_redis, InMemoryCache

logger = logging.getLogger(__name__)


class SalesStateStream:
    def __init__(self, stream_name: str = "stream:sales_state"):
        self.stream_name = stream_name
        self._last_turn: Dict[str, int] = {}

    async def publish(self, session_id: str, turn_id: int, state: Dict[str, Any]) -> bool:
        if self._last_turn.get(session_id) == turn_id:
            return False
        client = await get_redis()
        payload = {
            "session_id": session_id,
            "turn_id": turn_id,
            "timestamp": time.time(),
            "state": state,
        }
        try:
            await client.xadd(self.stream_name, {"data": json.dumps(payload, ensure_ascii=True)})
        except Exception as exc:
            logger.warning("State stream publish failed: %s", exc)
            return False
        self._last_turn[session_id] = turn_id
        await self._write_latest(session_id, state, turn_id)
        return True

    async def get_latest(self, session_id: str) -> Dict[str, Any]:
        client = await get_redis()
        key = f"sales_state:{session_id}"
        if isinstance(client, InMemoryCache):
            raw = getattr(client, "_store", {}).get(key)
        else:
            raw = await client.get(key)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except Exception:
            return {}

    async def replay(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        client = await get_redis()
        if isinstance(client, InMemoryCache):
            entries = await client.xrange(self.stream_name)
            return [json.loads(entry[1].get("data", "{}")) for entry in entries][-limit:]
        if hasattr(client, "xrevrange"):
            entries = await client.xrevrange(self.stream_name, count=limit)
            return [json.loads(entry[1].get("data", "{}")) for entry in entries]
        return []

    async def _write_latest(self, session_id: str, state: Dict[str, Any], turn_id: int) -> None:
        client = await get_redis()
        key = f"sales_state:{session_id}"
        payload = json.dumps({"turn_id": turn_id, "state": state}, ensure_ascii=True)
        try:
            await client.set(key, payload)
        except Exception as exc:
            logger.warning("Failed to write latest sales state: %s", exc)
