"""
Write-Ahead Logging (WAL) Manager
用于会话状态持久化与恢复
"""
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

class WALManager:
    """
    Write-Ahead Logging Manager using Redis Streams.
    
    Log Format:
    - stream_key: wal:{session_id}
    - fields:
        - turn: int
        - type: str (e.g., "USER_INPUT", "NPC_REPLY", "STATE_UPDATE")
        - payload: json_string
        - timestamp: iso_string
    """
    
    def __init__(self):
        self.redis = None

    async def _ensure_redis(self):
        if not self.redis:
            self.redis = await get_redis()

    async def log_event(
        self,
        session_id: str,
        turn_number: int,
        event_type: str,
        payload: Dict[str, Any]
    ) -> str:
        """
        Log an event to the session's WAL stream.
        Returns the message ID.
        """
        await self._ensure_redis()
        
        stream_key = f"wal:{session_id}"
        event_data = {
            "turn": str(turn_number),
            "type": event_type,
            "payload": json.dumps(payload, default=str),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check if redis client supports streams (might be InMemoryCache)
            if not hasattr(self.redis, "xadd"):
                logger.warning("WAL disabled: Redis backend does not support Streams (xadd)")
                return "0-0"
                
            msg_id = await self.redis.xadd(stream_key, event_data)
            return msg_id
        except Exception as e:
            logger.error(f"WAL log failed for {session_id}: {e}")
            raise e

    async def get_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all events for a session."""
        await self._ensure_redis()
        stream_key = f"wal:{session_id}"
        
        try:
            if not hasattr(self.redis, "xrange"):
                 return []
                 
            events = await self.redis.xrange(stream_key, min="-", max="+")
            parsed_events = []
            for msg_id, data in events:
                # Redis-py decode_responses=True returns strings, but sometimes byte keys?
                # Assuming decode_responses=True in get_redis
                payload_str = data.get("payload", "{}")
                if isinstance(payload_str, bytes):
                    payload_str = payload_str.decode("utf-8")
                
                parsed_events.append({
                    "msg_id": msg_id,
                    "turn": int(data.get("turn", 0)),
                    "type": data.get("type"),
                    "payload": json.loads(payload_str),
                    "timestamp": data.get("timestamp")
                })
            return parsed_events
        except Exception as e:
            logger.error(f"WAL read failed for {session_id}: {e}")
            return []

    async def clear_events(self, session_id: str) -> None:
        """Clear WAL for a session (e.g. on clean finish)."""
        await self._ensure_redis()
        stream_key = f"wal:{session_id}"
        try:
            await self.redis.delete(stream_key)
        except Exception as e:
            logger.error(f"WAL clear failed for {session_id}: {e}")

# Global instance
wal_manager = WALManager()
