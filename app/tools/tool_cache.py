from __future__ import annotations

import json
import logging
import time
from collections import OrderedDict
from difflib import SequenceMatcher
from typing import Any, Dict, Optional, Tuple

from core.config import get_settings


class ToolCache:
    def __init__(self) -> None:
        # Use OrderedDict for efficient LRU tracking
        self._entries: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._logger = logging.getLogger(__name__)

        # Statistics tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_accesses": 0,
            "by_tool": {}  # Per-tool statistics
        }

    async def get(self, tool_name: str, payload: Dict[str, Any]) -> Optional[Tuple[str, Any]]:
        settings = get_settings()
        if not settings.TOOL_CACHE_ENABLED or not settings.SEMANTIC_CACHE_ENABLED:
            return None
        if tool_name not in settings.TOOL_CACHE_TOOLS:
            return None

        now = time.time()
        ttl = settings.SEMANTIC_CACHE_TTL_SECONDS
        threshold = settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD
        query = (payload.get("query") or "").strip()

        # Update statistics
        self._stats["total_accesses"] += 1
        if tool_name not in self._stats["by_tool"]:
            self._stats["by_tool"][tool_name] = {"hits": 0, "misses": 0}

        # Exact match by signature
        signature = self._signature(tool_name, payload)
        entry = self._entries.get(signature)
        if entry and now - entry["timestamp"] <= ttl:
            # Update access tracking
            if settings.TOOL_CACHE_ACCESS_TRACKING:
                entry["access_count"] = entry.get("access_count", 0) + 1
                entry["last_accessed"] = now

                # Move to end for LRU (most recently used)
                if settings.TOOL_CACHE_LRU_ENABLED:
                    self._entries.move_to_end(signature)

            # Update statistics
            self._stats["hits"] += 1
            self._stats["by_tool"][tool_name]["hits"] += 1

            self._logger.info("[ToolCache] Hit for key: %s (tool=%s, type=exact)", signature, tool_name)
            return signature, entry["result"]

        # Semantic-ish match by query similarity
        if query:
            best_key = None
            best_score = 0.0
            for key, value in self._entries.items():
                if value.get("tool") != tool_name:
                    continue
                if now - value["timestamp"] > ttl:
                    continue
                cached_query = value.get("query", "")
                if not cached_query:
                    continue
                score = SequenceMatcher(None, query, cached_query).ratio()
                if score >= threshold and score > best_score:
                    best_score = score
                    best_key = key

            if best_key:
                entry = self._entries[best_key]

                # Update access tracking
                if settings.TOOL_CACHE_ACCESS_TRACKING:
                    entry["access_count"] = entry.get("access_count", 0) + 1
                    entry["last_accessed"] = now

                    # Move to end for LRU
                    if settings.TOOL_CACHE_LRU_ENABLED:
                        self._entries.move_to_end(best_key)

                # Update statistics
                self._stats["hits"] += 1
                self._stats["by_tool"][tool_name]["hits"] += 1

                self._logger.info(
                    "[ToolCache] Hit for key: %s (tool=%s, type=semantic, score=%.3f)",
                    best_key,
                    tool_name,
                    best_score,
                )
                return best_key, entry["result"]

        # Cache miss
        self._stats["misses"] += 1
        self._stats["by_tool"][tool_name]["misses"] += 1

        return None

    async def set(self, tool_name: str, payload: Dict[str, Any], result: Any) -> None:
        settings = get_settings()
        if not settings.TOOL_CACHE_ENABLED or not settings.SEMANTIC_CACHE_ENABLED:
            return
        if tool_name not in settings.TOOL_CACHE_TOOLS:
            return

        signature = self._signature(tool_name, payload)
        now = time.time()

        # Create entry with access tracking
        entry = {
            "tool": tool_name,
            "query": (payload.get("query") or "").strip(),
            "payload": payload,
            "result": result,
            "timestamp": now,
        }

        if settings.TOOL_CACHE_ACCESS_TRACKING:
            entry["access_count"] = 0
            entry["last_accessed"] = now

        self._entries[signature] = entry

        # Move to end (most recently added)
        if settings.TOOL_CACHE_LRU_ENABLED:
            self._entries.move_to_end(signature)

        # Trim cache if needed
        evicted = self._trim(settings.SEMANTIC_CACHE_MAX_ENTRIES)
        if evicted > 0:
            self._stats["evictions"] += evicted

    def _trim(self, max_entries: int) -> int:
        """
        Trim cache to max_entries using LRU policy.

        Returns:
            Number of entries evicted
        """
        settings = get_settings()
        evicted = 0

        if settings.TOOL_CACHE_LRU_ENABLED:
            # With LRU enabled, remove from the beginning (least recently used)
            while len(self._entries) > max_entries:
                # popitem(last=False) removes from beginning
                key, _ = self._entries.popitem(last=False)
                evicted += 1
                self._logger.debug(f"[ToolCache] Evicted LRU entry: {key}")
        else:
            # Without LRU, remove oldest entries by timestamp
            while len(self._entries) > max_entries:
                # Find oldest entry
                oldest_key = min(self._entries.keys(), key=lambda k: self._entries[k]["timestamp"])
                self._entries.pop(oldest_key)
                evicted += 1
                self._logger.debug(f"[ToolCache] Evicted oldest entry: {oldest_key}")

        return evicted

    def _signature(self, tool_name: str, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload or {}, sort_keys=True, ensure_ascii=True)
        return f"{tool_name}:{serialized}"

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics including:
            - hits: Total cache hits
            - misses: Total cache misses
            - hit_rate: Overall hit rate (0.0-1.0)
            - evictions: Total evictions
            - total_accesses: Total access attempts
            - size: Current cache size
            - by_tool: Per-tool statistics
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0

        # Calculate per-tool hit rates
        by_tool_stats = {}
        for tool_name, stats in self._stats["by_tool"].items():
            tool_total = stats["hits"] + stats["misses"]
            tool_hit_rate = stats["hits"] / tool_total if tool_total > 0 else 0.0
            by_tool_stats[tool_name] = {
                **stats,
                "hit_rate": tool_hit_rate
            }

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "total_accesses": self._stats["total_accesses"],
            "size": len(self._entries),
            "by_tool": by_tool_stats
        }

    def get_top_accessed(self, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Get top accessed cache entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of top accessed entries with metadata
        """
        settings = get_settings()
        if not settings.TOOL_CACHE_ACCESS_TRACKING:
            return []

        # Sort by access count
        sorted_entries = sorted(
            self._entries.items(),
            key=lambda x: x[1].get("access_count", 0),
            reverse=True
        )

        result = []
        for key, entry in sorted_entries[:limit]:
            result.append({
                "key": key,
                "tool": entry["tool"],
                "access_count": entry.get("access_count", 0),
                "last_accessed": entry.get("last_accessed"),
                "age_seconds": time.time() - entry["timestamp"]
            })

        return result

    def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        self._entries.clear()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_accesses": 0,
            "by_tool": {}
        }
        self._logger.info("[ToolCache] Cache cleared")

    def clear_tool(self, tool_name: str) -> int:
        """
        Clear cache entries for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Number of entries cleared
        """
        keys_to_remove = [
            key for key, entry in self._entries.items()
            if entry.get("tool") == tool_name
        ]

        for key in keys_to_remove:
            self._entries.pop(key)

        self._logger.info(f"[ToolCache] Cleared {len(keys_to_remove)} entries for tool: {tool_name}")
        return len(keys_to_remove)
