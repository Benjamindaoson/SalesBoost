"""Working Memory — Redis-backed current-session context."""
from __future__ import annotations

import json
from typing import Any

import structlog

from salesagent.core.settings import settings

log = structlog.get_logger()

_KEY_PREFIX = "wm:"


class WorkingMemory:
    """
    Stores the last N messages and session state for the current conversation.
    Backed by Redis hashes. TTL = 2 hours (configurable).
    """

    def __init__(self, redis: Any, session_id: str) -> None:
        self.redis = redis
        self.session_id = session_id
        self._messages_key = f"{_KEY_PREFIX}{session_id}:messages"
        self._state_key = f"{_KEY_PREFIX}{session_id}:state"
        self._max_messages = 20

    async def add_message(self, role: str, content: str) -> None:
        msg = json.dumps({"role": role, "content": content})
        await self.redis.rpush(self._messages_key, msg)
        await self.redis.ltrim(self._messages_key, -self._max_messages, -1)
        await self.redis.expire(self._messages_key, settings.working_memory_ttl_seconds)

    async def get_messages(self) -> list[dict[str, str]]:
        raw_list = await self.redis.lrange(self._messages_key, 0, -1)
        return [json.loads(r) for r in raw_list]

    async def set_state(self, key: str, value: Any) -> None:
        await self.redis.hset(self._state_key, key, json.dumps(value))
        await self.redis.expire(self._state_key, settings.working_memory_ttl_seconds)

    async def get_state(self, key: str) -> Any | None:
        raw = await self.redis.hget(self._state_key, key)
        return json.loads(raw) if raw else None

    async def clear(self) -> None:
        await self.redis.delete(self._messages_key, self._state_key)
