"""Time-decay formula for Adaptive Memory."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from salesagent.core.constants import MEMORY_HALF_LIFE


def effective_score(
    importance_score: float,
    last_accessed_at: datetime,
    entity_type: str = "default",
    now: datetime | None = None,
) -> float:
    """
    Compute effective importance with time decay:
        score = importance_score × 2^(-Δt / half_life)

    Args:
        importance_score: Raw importance [0, 1]
        last_accessed_at: Datetime of last access (timezone-aware)
        entity_type: Entity type key (maps to half-life in constants)
        now: Override for current time (useful in tests)

    Returns:
        Effective score [0, 1]
    """
    if now is None:
        now = datetime.now(timezone.utc)

    half_life_seconds = MEMORY_HALF_LIFE.get(entity_type, MEMORY_HALF_LIFE["default"])

    if half_life_seconds == float("inf"):
        return importance_score

    # Ensure both datetimes are tz-aware
    if last_accessed_at.tzinfo is None:
        last_accessed_at = last_accessed_at.replace(tzinfo=timezone.utc)

    delta_t = (now - last_accessed_at).total_seconds()
    if delta_t < 0:
        return importance_score  # future timestamp — treat as no decay

    decay_factor = math.pow(2.0, -delta_t / half_life_seconds)
    return importance_score * decay_factor
