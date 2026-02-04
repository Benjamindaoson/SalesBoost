"""Shadow model tracking."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from app.infra.cache.redis_client import redis_client

logger = logging.getLogger(__name__)


async def record_shadow_result(
    provider: str,
    model_name: str,
    payload: Dict[str, Any],
    max_entries: int = 1000,
) -> None:
    key = f"salesboost:shadow:{provider}/{model_name}"
    payload["timestamp"] = time.time()
    try:
        await redis_client.lpush(key, json.dumps(payload, ensure_ascii=True))
        await redis_client.ltrim(key, 0, max_entries - 1)
    except Exception as exc:
        logger.warning("Failed to record shadow result: %s", exc)
