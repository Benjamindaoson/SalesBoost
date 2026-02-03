"""
WebSocket State Recovery

Handles session state recovery after disconnect/reconnect.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StateRecoveryManager:
    """
    Manages WebSocket state recovery

    Features:
    - Save state on disconnect
    - Restore state on reconnect
    - Expire old states
    """

    def __init__(
        self,
        redis_client=None,
        ttl_seconds: int = 3600,  # 1 hour
    ):
        """
        Initialize state recovery manager

        Args:
            redis_client: Redis client (optional, uses in-memory if None)
            ttl_seconds: State TTL in seconds
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds

        # In-memory fallback
        self._memory_store: Dict[str, Dict[str, Any]] = {}

        logger.info("[StateRecovery] Initialized")

    async def save_state(
        self,
        session_id: str,
        user_id: str,
        state: Dict[str, Any]
    ):
        """
        Save session state

        Args:
            session_id: Session ID
            user_id: User ID
            state: State data to save
        """
        key = f"ws:state:{session_id}"

        state_data = {
            "user_id": user_id,
            "saved_at": datetime.utcnow().isoformat(),
            **state
        }

        if self.redis:
            # Save to Redis
            import json
            await self.redis.setex(
                key,
                self.ttl_seconds,
                json.dumps(state_data)
            )
        else:
            # Save to memory
            self._memory_store[key] = state_data

        logger.info(f"[StateRecovery] Saved state for session: {session_id}")

    async def restore_state(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Restore session state

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            Restored state or None if not found
        """
        key = f"ws:state:{session_id}"

        if self.redis:
            # Load from Redis
            import json
            data = await self.redis.get(key)

            if data:
                state = json.loads(data)

                # Verify user ID
                if state.get("user_id") != user_id:
                    logger.warning(
                        f"[StateRecovery] User ID mismatch for session: {session_id}"
                    )
                    return None

                logger.info(f"[StateRecovery] Restored state for session: {session_id}")
                return state

        else:
            # Load from memory
            state = self._memory_store.get(key)

            if state:
                # Verify user ID
                if state.get("user_id") != user_id:
                    logger.warning(
                        f"[StateRecovery] User ID mismatch for session: {session_id}"
                    )
                    return None

                # Check expiry
                saved_at = datetime.fromisoformat(state["saved_at"])
                if datetime.utcnow() - saved_at > timedelta(seconds=self.ttl_seconds):
                    logger.info(f"[StateRecovery] State expired for session: {session_id}")
                    del self._memory_store[key]
                    return None

                logger.info(f"[StateRecovery] Restored state for session: {session_id}")
                return state

        logger.info(f"[StateRecovery] No state found for session: {session_id}")
        return None

    async def delete_state(self, session_id: str):
        """Delete session state"""
        key = f"ws:state:{session_id}"

        if self.redis:
            await self.redis.delete(key)
        else:
            self._memory_store.pop(key, None)

        logger.info(f"[StateRecovery] Deleted state for session: {session_id}")
