import json
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import asdict

from app.services.memory.storage import MemoryStorage, UserProfile, MemoryEntry

logger = logging.getLogger(__name__)


class LocalMemoryStorage(MemoryStorage):
    """File-based implementation with tenant-aware separation."""

    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir = self.storage_dir / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)
        self.memories_dir = self.storage_dir / "memories"
        self.memories_dir.mkdir(exist_ok=True)

    def _get_profile_path(self, user_id: str, tenant_id: str = "public") -> Path:
        tenant_dir = self.profiles_dir / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        return tenant_dir / f"{user_id}.json"

    def _get_memory_path(self, user_id: str, tenant_id: str = "public") -> Path:
        tenant_dir = self.memories_dir / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        return tenant_dir / f"{user_id}_memories.json"

    def load_profile(self, user_id: str, tenant_id: str = "public") -> Optional[UserProfile]:
        path = self._get_profile_path(user_id, tenant_id)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return UserProfile(**data)
            except Exception as e:
                logger.error(f"Failed to load profile for {user_id}@{tenant_id}: {e}")
        return None

    def save_profile(self, profile: UserProfile):
        path = self._get_profile_path(profile.user_id, profile.tenant_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(profile), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile for {profile.user_id}@{profile.tenant_id}: {e}")

    def load_memories(self, user_id: str, tenant_id: str = "public") -> List[MemoryEntry]:
        path = self._get_memory_path(user_id, tenant_id)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [MemoryEntry(**m) for m in data]
        except Exception as e:
            logger.error(f"Failed to load memories for {user_id}@{tenant_id}: {e}")
            return []

    def save_memories(self, user_id: str, memories: List[MemoryEntry], tenant_id: str = "public"):
        path = self._get_memory_path(user_id, tenant_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                data = [asdict(m) for m in memories]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memories for {user_id}@{tenant_id}: {e}")
