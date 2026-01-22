import hashlib
import json
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any


@dataclass
class CacheEntry:
    value: Dict[str, Any]
    expires_at: float


class PromptCache:
    """
    前缀缓存/响应缓存，用于降低重复提示词开销。
    """

    def __init__(self, ttl_seconds: int = 600, max_entries: int = 512):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._store: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() > entry.expires_at:
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Dict[str, Any]) -> None:
        if len(self._store) >= self.max_entries:
            self._evict_oldest()
        self._store[key] = CacheEntry(
            value=value,
            expires_at=time.time() + self.ttl_seconds,
        )

    def build_key(
        self,
        messages: list[dict],
        model: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> str:
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _evict_oldest(self) -> None:
        if not self._store:
            return
        oldest_key = min(self._store.items(), key=lambda item: item[1].expires_at)[0]
        self._store.pop(oldest_key, None)
