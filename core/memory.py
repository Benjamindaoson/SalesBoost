"""
Backward-compatible memory manager backed by MemoryService.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.cognitive.memory.storage.backends.memory.storage import UserProfile
from app.cognitive.memory.storage.profile_service import MemoryService, memory_service


class MemoryManager:
    """Thin wrapper around the persistent MemoryService."""

    def __init__(self, service: MemoryService) -> None:
        self._service = service

    async def add_episodic_memory(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "user_default",
    ) -> None:
        await self._service.add_long_term_memory(
            user_id=user_id,
            content=content,
            category="episodic",
            session_id=session_id,
            metadata={"role": role, **(metadata or {})},
        )

    async def get_user_profile(self, user_id: str, tenant_id: str = "public") -> UserProfile:
        return await self._service.get_or_create_profile(user_id, tenant_id)

    async def get_relevant_context(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
        tenant_id: str = "public",
    ) -> str:
        return await self._service.get_relevant_context(user_id, query=query, tenant_id=tenant_id)


memory_manager = MemoryManager(memory_service)

