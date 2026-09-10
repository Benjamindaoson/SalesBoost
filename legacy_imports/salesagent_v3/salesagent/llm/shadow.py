"""Shadow Mode — async traffic splitting for A/B model comparison."""
from __future__ import annotations

import asyncio
import random
from typing import Any

import structlog

from salesagent.core.settings import settings

log = structlog.get_logger()


class ShadowMode:
    """
    Intercepts SHADOW_MODE_RATIO of requests, runs them through a shadow model
    asynchronously (without blocking the main response), and stores both outputs
    for Reward comparison in the data flywheel.
    """

    def __init__(self, gateway: Any, redis: Any) -> None:
        self.gateway = gateway
        self.redis = redis

    def should_shadow(self) -> bool:
        return settings.shadow_mode_enabled and random.random() < settings.shadow_mode_ratio

    async def run_shadow(
        self,
        session_id: str,
        turn_index: int,
        system: str,
        user: str,
        main_response: str,
    ) -> None:
        """Fire-and-forget shadow call. Called after main response is sent."""
        if not self.should_shadow():
            return

        asyncio.create_task(
            self._execute_shadow(session_id, turn_index, system, user, main_response)
        )

    async def _execute_shadow(
        self,
        session_id: str,
        turn_index: int,
        system: str,
        user: str,
        main_response: str,
    ) -> None:
        try:
            shadow_response = await self.gateway.complete(
                task="response",
                system=system,
                user=user,
                session_id=f"shadow:{session_id}",
            )

            # Store for Reward Model comparison
            from salesagent.core.constants import REDIS_STREAM_FLYWHEEL
            import json

            await self.redis.xadd(
                REDIS_STREAM_FLYWHEEL,
                {
                    "type": "shadow_comparison",
                    "session_id": session_id,
                    "turn_index": str(turn_index),
                    "main_model": settings.primary_response_model,
                    "shadow_model": settings.shadow_model,
                    "main_response": main_response,
                    "shadow_response": shadow_response,
                },
                maxlen=5_000,
                approximate=True,
            )

            log.debug("Shadow call completed", session_id=session_id, turn_index=turn_index)

        except Exception as exc:
            log.warning("Shadow call failed", error=str(exc))
