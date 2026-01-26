"""
Persistent memory service with Redis or local storage backends.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.redis import get_redis
from app.services.memory.local_storage import LocalMemoryStorage
from app.services.memory.sqlite_storage import SqliteMemoryStorage
from app.services.memory.storage import MemoryEntry, UserProfile, MemoryStorage

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryService:
    """
    Memory service that stores long-term memories and user profiles.
    """

    def __init__(
        self,
        storage: Optional[MemoryStorage] = None,
        backend: Optional[str] = None,
    ) -> None:
        self.backend = (backend or settings.MEMORY_STORAGE_BACKEND or "local").lower()
        if self.backend not in {"redis", "sqlite", "db", "local"}:
            logger.warning("Unknown memory backend '%s', falling back to sqlite", self.backend)
            self.backend = "sqlite"
        self._storage = storage
        self._redis_client = None
        if self.backend in {"sqlite", "db"} and self._storage is None:
            db_path = settings.MEMORY_STORAGE_PATH
            if not db_path.endswith(".db"):
                db_path = str(Path(db_path) / "memory.db")
            self._storage = SqliteMemoryStorage(db_path)
        if self.backend == "local" and self._storage is None:
            self._storage = LocalMemoryStorage(settings.MEMORY_STORAGE_PATH)

    async def _get_redis_client(self):
        if self._redis_client is None:
            self._redis_client = await get_redis()
        return self._redis_client

    def _profile_key(self, user_id: str, tenant_id: str) -> str:
        return f"memory:{tenant_id}:{user_id}:profile"

    def _memories_key(self, user_id: str, tenant_id: str) -> str:
        return f"memory:{tenant_id}:{user_id}:memories"

    async def load_profile(self, user_id: str, tenant_id: str = "public") -> Optional[UserProfile]:
        if self.backend == "redis":
            client = await self._get_redis_client()
            raw = await client.get(self._profile_key(user_id, tenant_id))
            if not raw:
                return None
            try:
                return UserProfile(**json.loads(raw))
            except Exception as exc:
                logger.warning("Failed to parse profile for %s@%s: %s", user_id, tenant_id, exc)
                return None

        if not self._storage:
            return None
        return await asyncio.to_thread(self._storage.load_profile, user_id, tenant_id)

    async def save_profile(self, profile: UserProfile) -> None:
        if self.backend == "redis":
            client = await self._get_redis_client()
            payload = json.dumps(profile.__dict__, ensure_ascii=True)
            await client.set(self._profile_key(profile.user_id, profile.tenant_id), payload)
            return

        if not self._storage:
            return
        await asyncio.to_thread(self._storage.save_profile, profile)

    async def load_memories(self, user_id: str, tenant_id: str = "public") -> List[MemoryEntry]:
        if self.backend == "redis":
            client = await self._get_redis_client()
            raw = await client.get(self._memories_key(user_id, tenant_id))
            if not raw:
                return []
            try:
                data = json.loads(raw)
                return [MemoryEntry(**m) for m in data]
            except Exception as exc:
                logger.warning("Failed to parse memories for %s@%s: %s", user_id, tenant_id, exc)
                return []

        if not self._storage:
            return []
        return await asyncio.to_thread(self._storage.load_memories, user_id, tenant_id)

    async def save_memories(self, user_id: str, memories: List[MemoryEntry], tenant_id: str = "public") -> None:
        if self.backend == "redis":
            client = await self._get_redis_client()
            payload = json.dumps([m.__dict__ for m in memories], ensure_ascii=True)
            await client.set(self._memories_key(user_id, tenant_id), payload)
            return

        if not self._storage:
            return
        await asyncio.to_thread(self._storage.save_memories, user_id, memories, tenant_id)

    async def get_or_create_profile(self, user_id: str, tenant_id: str = "public") -> UserProfile:
        profile = await self.load_profile(user_id, tenant_id)
        if profile:
            return profile
        profile = UserProfile(user_id=user_id, tenant_id=tenant_id)
        await self.save_profile(profile)
        return profile

    async def add_long_term_memory(
        self,
        user_id: str,
        content: str,
        category: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tenant_id: str = "public",
        max_entries: int = 200,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            category=category,
            session_id=session_id,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat(),
        )
        memories = await self.load_memories(user_id, tenant_id)
        memories.append(entry)
        if len(memories) > max_entries:
            memories = memories[-max_entries:]
        await self.save_memories(user_id, memories, tenant_id)
        return entry

    async def update_skill_level(
        self,
        user_id: str,
        skill_name: str,
        delta: float,
        tenant_id: str = "public",
    ) -> UserProfile:
        profile = await self.get_or_create_profile(user_id, tenant_id)
        current = profile.skill_levels.get(skill_name, 0.5)
        updated = max(0.0, min(1.0, current + delta))
        profile.skill_levels[skill_name] = updated
        profile.updated_at = datetime.utcnow().isoformat()
        await self.save_profile(profile)
        return profile

    async def get_relevant_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        tenant_id: str = "public",
        max_items: int = 5,
    ) -> str:
        profile = await self.get_or_create_profile(user_id, tenant_id)
        memories = await self.load_memories(user_id, tenant_id)
        if query:
            lowered = query.lower()
            filtered = [m for m in memories if lowered in m.content.lower()]
        else:
            filtered = memories
        recent = filtered[-max_items:]
        memory_lines = [f"- {m.content}" for m in recent]
        profile_summary = f"User skill levels: {profile.skill_levels}"
        return "\n".join([profile_summary, "Recent memories:"] + memory_lines) if memory_lines else profile_summary


memory_service = MemoryService()
