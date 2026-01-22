import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    key: str
    value: Any
    scope: str
    timestamp: str
    ttl_seconds: Optional[int] = None


class ContextBus:
    """
    多智能体共享上下文黑板
    - 仅同步关键状态，避免全量广播
    - 支持 agent 视图过滤
    """

    DEFAULT_AGENT_KEYS = {
        "rag": {"state", "intent", "memory", "user_profile"},
        "coach": {"state", "intent", "memory", "strategy"},
        "evaluator": {"state", "intent", "memory"},
        "npc": {"state", "memory"},
    }

    def __init__(self):
        self._entries: Dict[str, ContextEntry] = {}

    def reset(self) -> None:
        self._entries.clear()

    def publish(
        self,
        key: str,
        value: Any,
        scope: str = "session",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        self._entries[key] = ContextEntry(
            key=key,
            value=value,
            scope=scope,
            timestamp=datetime.utcnow().isoformat(),
            ttl_seconds=ttl_seconds,
        )

    def bulk_publish(self, payload: Dict[str, Any], scope: str = "session") -> None:
        for key, value in payload.items():
            self.publish(key, value, scope=scope)

    def view_for(self, agent_name: str, include_keys: Optional[set[str]] = None) -> Dict[str, Any]:
        keys = include_keys or self.DEFAULT_AGENT_KEYS.get(agent_name, set())
        snapshot = {}
        for key in keys:
            entry = self._entries.get(key)
            if entry:
                snapshot[key] = entry.value
        return snapshot
