"""Memory tier storage for context manager."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from core.redis import get_redis, InMemoryCache

logger = logging.getLogger(__name__)

# Redis Lua script: LPUSH + LTRIM in one atomic operation.
_S0_LUA = """
local key = KEYS[1]
local msg = ARGV[1]
local max_len = tonumber(ARGV[2])
redis.call('LPUSH', key, msg)
redis.call('LTRIM', key, 0, max_len - 1)
return redis.call('LLEN', key)
"""


class ContextMemoryStore:
    def __init__(self, max_s0: int = 10):
        self.max_s0 = max_s0
        self._s0: Dict[str, List[Dict[str, str]]] = {}
        self._s0_script = None

    async def append_s0(self, session_id: str, message: Dict[str, str]) -> List[Dict[str, str]]:
        key = f"ctx:s0:{{{session_id}}}"
        message_json = json.dumps(message, ensure_ascii=True)

        client = await get_redis()
        if isinstance(client, InMemoryCache):
            buffer = self._s0.setdefault(session_id, [])
            buffer.append(message)
            if len(buffer) > self.max_s0:
                self._s0[session_id] = buffer[-self.max_s0 :]
            return self._s0[session_id]

        try:
            if self._s0_script is None:
                self._s0_script = client.register_script(_S0_LUA)
            await self._s0_script(keys=[key], args=[message_json, str(self.max_s0)])
        except Exception as exc:
            logger.warning("Redis S0 update failed, falling back to local buffer: %s", exc)
            buffer = self._s0.setdefault(session_id, [])
            buffer.append(message)
            if len(buffer) > self.max_s0:
                self._s0[session_id] = buffer[-self.max_s0 :]
            return self._s0[session_id]

        # Notify other modules asynchronously via Redis Streams.
        try:
            stream_key = f"stream:ctx_update:{{{session_id}}}"
            await client.xadd(stream_key, {"session_id": session_id, "event": "s0_updated"}, maxlen=1000)
        except Exception as exc:
            logger.warning("Failed to publish context update event: %s", exc)

        return await self.get_s0(session_id)

    async def get_s0(self, session_id: str) -> List[Dict[str, str]]:
        key = f"ctx:s0:{{{session_id}}}"
        client = await get_redis()
        if isinstance(client, InMemoryCache):
            return self._s0.get(session_id, [])
        try:
            raw_items = await client.lrange(key, 0, self.max_s0 - 1)
            result: List[Dict[str, str]] = []
            for item in reversed(raw_items):
                try:
                    result.append(json.loads(item))
                except Exception:
                    continue
            return result
        except Exception as exc:
            logger.warning("Failed to read S0 from Redis: %s", exc)
            return self._s0.get(session_id, [])

    async def write_s1(self, session_id: str, summary: Dict[str, Any]) -> None:
        await self._write_json(f"ctx:s1:{session_id}", summary)

    async def write_s2(self, user_id: str, profile: Dict[str, Any]) -> None:
        if not user_id:
            return
        await self._write_json(f"ctx:s2:{user_id}", profile)

    async def write_s3(self, tenant_id: str, knowledge: Dict[str, Any]) -> None:
        if not tenant_id:
            return
        await self._write_json(f"ctx:s3:{tenant_id}", knowledge)

    async def read_json(self, key: str) -> Dict[str, Any]:
        client = await get_redis()
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

    async def _write_json(self, key: str, payload: Dict[str, Any]) -> None:
        client = await get_redis()
        data = json.dumps(payload, ensure_ascii=True)
        try:
            await client.set(key, data)
        except Exception as exc:
            logger.warning("Failed to write %s: %s", key, exc)
