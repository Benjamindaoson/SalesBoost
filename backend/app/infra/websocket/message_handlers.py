"""
WebSocket Message Handlers

Extracted message handling logic from monolithic websocket.py

Each handler is responsible for a specific message type.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageHandler:
    """Base class for message handlers"""

    async def handle(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle message

        Args:
            data: Message data
            session_id: Session ID
            user_id: User ID
            context: Handler context (connection manager, coordinator, etc.)

        Returns:
            Response message (None if no response needed)
        """
        raise NotImplementedError


class UserMessageHandler(MessageHandler):
    """Handle user chat messages"""

    async def handle(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle user message"""
        content = data.get("content", "")
        turn_id = data.get("turn_id")

        if not content:
            return {
                "type": "error",
                "error": "Empty message content"
            }

        # Get coordinator
        coordinator = context["coordinator"]
        turn_number = context.get("turn_number", 1)

        # Execute turn
        try:
            result = await coordinator.execute_turn(
                turn_number=turn_number,
                user_message=content,
                enable_async_coach=True  # TTFT optimization
            )

            # Send NPC response
            await context["connection_manager"].send_json(session_id, {
                "type": "npc_response",
                "content": result.npc_response,
                "mood": result.npc_mood,
                "intent": result.intent,
                "turn_id": turn_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Send coach advice asynchronously if available
            if result.coach_advice:
                await context["connection_manager"].send_json(session_id, {
                    "type": "coach_advice",
                    "advice": result.coach_advice,
                    "source": result.advice_source,
                    "turn_id": turn_id,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Update context
            context["turn_number"] = turn_number + 1

            return None  # Already sent responses

        except Exception as e:
            logger.error(f"[UserMessageHandler] Error: {e}", exc_info=True)
            return {
                "type": "error",
                "error": str(e),
                "turn_id": turn_id
            }


class AckHandler(MessageHandler):
    """Handle acknowledgment messages"""

    async def handle(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle ACK"""
        seq_id = data.get("sequence")

        if seq_id is not None:
            await context["connection_manager"].ack_chunk(session_id, seq_id)

        return None


class PingHandler(MessageHandler):
    """Handle ping messages"""

    async def handle(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle ping"""
        return {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }


class FeedbackHandler(MessageHandler):
    """Handle user feedback"""

    async def handle(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle feedback"""
        rating = data.get("rating")
        comment = data.get("comment")
        turn_id = data.get("turn_id")

        # Record feedback (bandit learning)
        coordinator = context["coordinator"]

        if hasattr(coordinator, "record_bandit_feedback"):
            # Convert rating to reward (1-5 → 0-1)
            reward = (rating - 1) / 4 if rating else 0.5

            await coordinator.record_bandit_feedback(
                decision_id=None,  # Use last decision
                reward=reward,
                signals={"comment": comment}
            )

        logger.info(
            f"[FeedbackHandler] Received feedback: "
            f"rating={rating}, turn_id={turn_id}"
        )

        return {
            "type": "feedback_received",
            "turn_id": turn_id
        }


# ==================== Message Router ====================

class MessageRouter:
    """Routes messages to appropriate handlers"""

    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {
            "user_message": UserMessageHandler(),
            "ack": AckHandler(),
            "ping": PingHandler(),
            "feedback": FeedbackHandler(),
        }

    def register_handler(self, message_type: str, handler: MessageHandler):
        """Register custom handler"""
        self.handlers[message_type] = handler

    async def route(
        self,
        message: Dict[str, Any],
        session_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Route message to handler

        Args:
            message: Message data
            session_id: Session ID
            user_id: User ID
            context: Handler context

        Returns:
            Response message (None if no response)
        """
        message_type = message.get("type")

        if not message_type:
            return {
                "type": "error",
                "error": "Missing message type"
            }

        handler = self.handlers.get(message_type)

        if not handler:
            logger.warning(f"[MessageRouter] Unknown message type: {message_type}")
            return {
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            }

        return await handler.handle(message, session_id, user_id, context)
