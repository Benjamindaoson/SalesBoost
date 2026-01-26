from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class MemoryEntry:
    id: str
    content: str
    category: str
    session_id: Optional[str]
    metadata: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class UserProfile:
    user_id: str
    tenant_id: str = "public"
    skill_levels: Dict[str, float] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryStorage(ABC):
    @abstractmethod
    def load_profile(self, user_id: str, tenant_id: str = "public") -> Optional[UserProfile]:
        raise NotImplementedError

    @abstractmethod
    def save_profile(self, profile: UserProfile) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_memories(self, user_id: str, tenant_id: str = "public") -> List[MemoryEntry]:
        raise NotImplementedError

    @abstractmethod
    def save_memories(self, user_id: str, memories: List[MemoryEntry], tenant_id: str = "public") -> None:
        raise NotImplementedError
