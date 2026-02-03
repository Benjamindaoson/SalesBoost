"""State snapshot with Redis persistence and deep serialization."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any
from datetime import datetime

from core.redis import get_redis
from app.engine.state.serializers import deep_serializer

logger = logging.getLogger(__name__)

@dataclass
class Snapshot:
    """Enhanced snapshot with deep serialization support."""
    snapshot_id: str
    session_id: str
    user_id: str
    current_stage: str
    context: dict
    fsm_state: Optional[dict] = None
    conversation_history: Optional[list] = None
    agent_context: Optional[dict] = None
    created_at: Optional[str] = None
    suspension_reason: Optional[str] = None

class StateSnapshotService:
    def __init__(self) -> None:
        self.prefix = "salesboost:snapshot:"

    async def create_snapshot(
        self,
        snapshot_id: str,
        session_id: str,
        user_id: str,
        current_stage: str,
        context: dict,
        fsm_state: Optional[Any] = None,
        conversation_history: Optional[list] = None,
        agent_context: Optional[dict] = None,
        suspension_reason: Optional[str] = None
    ) -> Snapshot:
        """
        Create a snapshot with deep serialization support.
        
        Handles complex objects including FSM state, conversation history,
        and agent context. Uses deep serialization to handle circular
        references and non-JSON-serializable objects.
        
        Args:
            snapshot_id: Unique snapshot identifier
            session_id: Session identifier
            user_id: User identifier
            current_stage: Current sales stage
            context: Session context dictionary
            fsm_state: Optional FSM state object
            conversation_history: Optional conversation history
            agent_context: Optional agent context
            suspension_reason: Optional reason for suspension
            
        Returns:
            Created Snapshot object
        """
        # Serialize complex objects
        serialized_fsm = None
        if fsm_state is not None:
            try:
                serialized_fsm = deep_serializer.serialize(fsm_state)
            except Exception as e:
                logger.error(f"Failed to serialize FSM state: {e}")
                serialized_fsm = {"_error": str(e)}
        
        serialized_agent_context = None
        if agent_context is not None:
            try:
                serialized_agent_context = deep_serializer.serialize(agent_context)
            except Exception as e:
                logger.error(f"Failed to serialize agent context: {e}")
                serialized_agent_context = {"_error": str(e)}
        
        snapshot = Snapshot(
            snapshot_id=snapshot_id,
            session_id=session_id,
            user_id=user_id,
            current_stage=current_stage,
            context=context,
            fsm_state=serialized_fsm,
            conversation_history=conversation_history,
            agent_context=serialized_agent_context,
            created_at=datetime.utcnow().isoformat(),
            suspension_reason=suspension_reason
        )
        
        redis = await get_redis()
        key = f"{self.prefix}{snapshot_id}"
        
        # Serialize snapshot to JSON
        snapshot_dict = asdict(snapshot)
        await redis.set(key, json.dumps(snapshot_dict), ex=3600 * 24)  # 24h TTL
        
        logger.info(
            f"Created snapshot in Redis: {snapshot_id} "
            f"(session: {session_id}, reason: {suspension_reason or 'manual'})"
        )
        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """
        Retrieve a snapshot from Redis.
        
        Args:
            snapshot_id: Snapshot identifier
            
        Returns:
            Snapshot object or None if not found
        """
        redis = await get_redis()
        key = f"{self.prefix}{snapshot_id}"
        data = await redis.get(key)
        
        if data:
            snapshot_dict = json.loads(data)
            return Snapshot(**snapshot_dict)
        return None
    
    async def restore_fsm_state(self, snapshot: Snapshot) -> Optional[Any]:
        """
        Restore FSM state from snapshot.
        
        Args:
            snapshot: Snapshot containing serialized FSM state
            
        Returns:
            Restored FSM state object or None
        """
        if not snapshot.fsm_state:
            return None
        
        try:
            return deep_serializer.deserialize(snapshot.fsm_state)
        except Exception as e:
            logger.error(f"Failed to deserialize FSM state: {e}")
            return None
    
    async def restore_agent_context(self, snapshot: Snapshot) -> Optional[dict]:
        """
        Restore agent context from snapshot.
        
        Args:
            snapshot: Snapshot containing serialized agent context
            
        Returns:
            Restored agent context dictionary or None
        """
        if not snapshot.agent_context:
            return None
        
        try:
            return deep_serializer.deserialize(snapshot.agent_context)
        except Exception as e:
            logger.error(f"Failed to deserialize agent context: {e}")
            return None

    async def delete_snapshot(self, snapshot_id: str) -> bool:
        redis = await get_redis()
        key = f"{self.prefix}{snapshot_id}"
        result = await redis.delete(key)
        return result > 0

state_snapshot_service = StateSnapshotService()
