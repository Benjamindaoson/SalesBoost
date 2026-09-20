"""Memory runtime tracing primitives.

Tracks whether retrieved memories are available and attributable during agent
execution. Used by evaluation and future ProductionCoordinator hooks.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime, timezone


@dataclass
class MemoryTrace:
    session_id: str
    query: str
    retrieved: List[Dict[str, Any]] = field(default_factory=list)
    used_by_agent: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def mark_used(self) -> None:
        self.used_by_agent = True

    @property
    def hit_count(self) -> int:
        return len(self.retrieved)
