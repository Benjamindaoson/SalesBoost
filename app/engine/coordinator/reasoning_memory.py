"""
Memory Buffer for Reasoning Engine
Stores and retrieves historical reasoning results for context-aware analysis
"""
from collections import deque
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ReasoningMemoryBuffer:
    """
    Memory Buffer for storing historical reasoning results

    Features:
    - Fixed-size circular buffer (FIFO)
    - Session-based isolation
    - Redis persistence (optional)
    - Context retrieval for similar situations

    Usage:
        buffer = ReasoningMemoryBuffer(max_size=10)

        # Store reasoning
        buffer.add(
            session_id="session_123",
            turn_number=1,
            reasoning={
                "analysis": ["User is greeting"],
                "core_concern": "establish rapport",
                "strategy": "friendly response"
            }
        )

        # Retrieve recent reasoning
        history = buffer.get_recent(session_id="session_123", n=3)

        # Get context for current situation
        context = buffer.get_context_summary(session_id="session_123")
    """

    def __init__(
        self,
        max_size: int = 10,
        redis_client: Optional[Any] = None,
        persist: bool = True
    ):
        """
        Initialize memory buffer

        Args:
            max_size: Maximum number of reasoning entries per session
            redis_client: Optional Redis client for persistence
            persist: Whether to persist to Redis
        """
        self.max_size = max_size
        self.redis_client = redis_client
        self.persist = persist

        # In-memory storage: {session_id: deque of reasoning entries}
        self._memory: Dict[str, deque] = {}

    def add(
        self,
        session_id: str,
        turn_number: int,
        reasoning: Dict[str, Any],
        intent: Optional[str] = None,
        confidence: Optional[float] = None
    ):
        """
        Add reasoning result to memory

        Args:
            session_id: Session ID
            turn_number: Turn number
            reasoning: Reasoning result dictionary
            intent: Detected intent
            confidence: Intent confidence
        """
        entry = {
            "turn_number": turn_number,
            "reasoning": reasoning,
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add to in-memory buffer
        if session_id not in self._memory:
            self._memory[session_id] = deque(maxlen=self.max_size)

        self._memory[session_id].append(entry)

        # Persist to Redis
        if self.persist and self.redis_client:
            self._persist_to_redis(session_id)

        logger.debug(
            f"[ReasoningMemory] Added entry: session={session_id}, "
            f"turn={turn_number}, intent={intent}"
        )

    def get_recent(
        self,
        session_id: str,
        n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get N most recent reasoning entries

        Args:
            session_id: Session ID
            n: Number of entries to retrieve

        Returns:
            List of reasoning entries (most recent first)
        """
        if session_id not in self._memory:
            # Try loading from Redis
            if self.redis_client:
                self._load_from_redis(session_id)

        if session_id not in self._memory:
            return []

        # Get last N entries
        entries = list(self._memory[session_id])
        return entries[-n:][::-1]  # Reverse to get most recent first

    def get_context_summary(
        self,
        session_id: str,
        max_entries: int = 5
    ) -> str:
        """
        Get a text summary of recent reasoning for context

        Args:
            session_id: Session ID
            max_entries: Maximum number of entries to include

        Returns:
            Formatted context summary
        """
        recent = self.get_recent(session_id, max_entries)

        if not recent:
            return "No previous reasoning history."

        summary_parts = ["Previous reasoning history:"]

        for i, entry in enumerate(recent, 1):
            reasoning = entry.get("reasoning", {})
            intent = entry.get("intent", "unknown")
            turn = entry.get("turn_number", 0)

            core_concern = reasoning.get("core_concern", "N/A")
            strategy = reasoning.get("strategy", "N/A")

            summary_parts.append(
                f"{i}. Turn {turn} ({intent}): "
                f"Concern='{core_concern}', Strategy='{strategy}'"
            )

        return "\n".join(summary_parts)

    def get_similar_situations(
        self,
        session_id: str,
        current_intent: str,
        n: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get reasoning from similar situations (same intent)

        Args:
            session_id: Session ID
            current_intent: Current intent to match
            n: Number of similar situations to retrieve

        Returns:
            List of similar reasoning entries
        """
        if session_id not in self._memory:
            return []

        # Filter by intent
        similar = [
            entry for entry in self._memory[session_id]
            if entry.get("intent") == current_intent
        ]

        # Return most recent N
        return similar[-n:][::-1]

    def clear(self, session_id: str):
        """Clear memory for a session"""
        if session_id in self._memory:
            del self._memory[session_id]

        # Clear from Redis
        if self.redis_client:
            try:
                key = f"reasoning_memory:{session_id}"
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"[ReasoningMemory] Failed to clear Redis: {e}")

    def _persist_to_redis(self, session_id: str):
        """Persist memory to Redis"""
        if not self.redis_client:
            return

        try:
            key = f"reasoning_memory:{session_id}"
            entries = list(self._memory[session_id])
            data = json.dumps(entries)

            # Store with 24 hour TTL
            self.redis_client.setex(key, 86400, data)

        except Exception as e:
            logger.warning(f"[ReasoningMemory] Failed to persist to Redis: {e}")

    def _load_from_redis(self, session_id: str):
        """Load memory from Redis"""
        if not self.redis_client:
            return

        try:
            key = f"reasoning_memory:{session_id}"
            data = self.redis_client.get(key)

            if data:
                entries = json.loads(data)
                self._memory[session_id] = deque(entries, maxlen=self.max_size)
                logger.debug(
                    f"[ReasoningMemory] Loaded {len(entries)} entries from Redis"
                )

        except Exception as e:
            logger.warning(f"[ReasoningMemory] Failed to load from Redis: {e}")

    def get_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session's memory"""
        if session_id not in self._memory:
            return {
                "total_entries": 0,
                "intents": {},
                "avg_confidence": 0.0
            }

        entries = list(self._memory[session_id])

        # Count intents
        intent_counts = {}
        confidences = []

        for entry in entries:
            intent = entry.get("intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

            confidence = entry.get("confidence")
            if confidence is not None:
                confidences.append(confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_entries": len(entries),
            "intents": intent_counts,
            "avg_confidence": avg_confidence
        }


# ==================== Global Instance ====================

_memory_buffer: Optional[ReasoningMemoryBuffer] = None


def get_reasoning_memory() -> ReasoningMemoryBuffer:
    """Get global reasoning memory buffer"""
    global _memory_buffer

    if _memory_buffer is None:
        try:
            from core.redis import get_redis_sync
            redis_client = get_redis_sync()
        except:
            redis_client = None

        _memory_buffer = ReasoningMemoryBuffer(
            max_size=10,
            redis_client=redis_client,
            persist=True
        )

    return _memory_buffer
