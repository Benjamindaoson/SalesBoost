"""
WebSocket endpoint for Human-in-the-Loop review.
Allows administrators to review and approve/reject/modify flagged content.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime

from app.engine.coordinator.human_in_loop_coordinator import HumanReviewDecision
from app.engine.coordinator.production_coordinator import get_human_review_coordinator

logger = logging.getLogger(__name__)
router = APIRouter()


class ReviewConnectionManager:
    """Manage admin review WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.admin_sessions: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, admin_id: str):
        """Accept and register an admin connection."""
        await websocket.accept()
        connection_id = f"admin_{admin_id}_{datetime.utcnow().timestamp()}"
        self.active_connections[connection_id] = websocket
        self.admin_sessions[admin_id] = connection_id
        logger.info("[ReviewManager] Admin %s connected", admin_id)

    async def disconnect(self, admin_id: str):
        """Disconnect an admin session."""
        connection_id = self.admin_sessions.pop(admin_id, None)
        if connection_id:
            self.active_connections.pop(connection_id, None)
            logger.info("[ReviewManager] Admin %s disconnected", admin_id)

    async def broadcast_pending_review(self, session_id: str, review_data: Dict[str, Any]):
        """Broadcast a pending review to all connected admins."""
        notification = {
            "type": "new_review_request",
            "session_id": session_id,
            "data": review_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        disconnected = []
        for admin_id, connection_id in self.admin_sessions.items():
            websocket = self.active_connections.get(connection_id)
            if websocket:
                try:
                    await websocket.send_json(notification)
                except Exception as e:
                    logger.error("Failed to send to %s: %s", admin_id, e)
                    disconnected.append(admin_id)

        for admin_id in disconnected:
            await self.disconnect(admin_id)


review_manager = ReviewConnectionManager()


@router.websocket("/ws/admin/review")
async def admin_review_websocket(
    websocket: WebSocket,
    admin_id: str,
    # admin_user = Depends(require_admin_user)
):
    """
    Admin review WebSocket.

    Protocol:
        Client -> Server:
            {
                "action": "approve" | "reject" | "modify",
                "session_id": "session_123",
                "modified_content": "..."  // required when action=modify
            }

        Server -> Client:
            {
                "type": "new_review_request",
                "session_id": "session_123",
                "data": {
                    "risk_score": 0.85,
                    "violations": [...],
                    "npc_response": "...",
                    "timestamp": "2026-01-29T..."
                }
            }

            {
                "type": "review_completed",
                "session_id": "session_123",
                "decision": "approve",
                "reviewer": "admin_1"
            }
    """
    await review_manager.connect(websocket, admin_id)

    try:
        coordinator = get_human_review_coordinator()
        pending_reviews = coordinator.get_pending_reviews()

        await websocket.send_json({
            "type": "pending_reviews",
            "reviews": pending_reviews,
            "count": len(pending_reviews),
        })

        async for message in websocket.iter_json():
            action = message.get("action")
            session_id = message.get("session_id")

            if not action or not session_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "Missing action or session_id",
                })
                continue

            try:
                if action == "approve":
                    await coordinator.resume_after_review(
                        session_id,
                        decision=HumanReviewDecision.APPROVE,
                        admin_id=admin_id,
                    )
                elif action == "reject":
                    await coordinator.resume_after_review(
                        session_id,
                        decision=HumanReviewDecision.REJECT,
                        admin_id=admin_id,
                    )
                elif action == "modify":
                    modified_content = message.get("modified_content")
                    if not modified_content:
                        raise ValueError("modified_content is required")

                    await coordinator.resume_after_review(
                        session_id,
                        decision=HumanReviewDecision.MODIFY,
                        modified_content=modified_content,
                        admin_id=admin_id,
                    )
                else:
                    raise ValueError(f"Invalid action: {action}")

                await websocket.send_json({
                    "type": "review_completed",
                    "session_id": session_id,
                    "decision": action,
                    "reviewer": admin_id,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                await review_manager.broadcast_pending_review(
                    session_id,
                    {"status": "completed", "reviewer": admin_id},
                )

            except Exception as e:
                logger.error("[ReviewWS] Error processing review: %s", e)
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "session_id": session_id,
                })

    except WebSocketDisconnect:
        logger.info("[ReviewWS] Admin %s disconnected", admin_id)
    finally:
        await review_manager.disconnect(admin_id)


@router.get("/api/admin/reviews/pending")
async def get_pending_reviews(
    # admin_user = Depends(require_admin_user)
):
    """Get pending reviews (HTTP)."""
    coordinator = get_human_review_coordinator()
    pending_reviews = coordinator.get_pending_reviews()

    return {
        "reviews": pending_reviews,
        "count": len(pending_reviews),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/api/admin/reviews/{session_id}/approve")
async def approve_review(
    session_id: str,
    # admin_user = Depends(require_admin_user)
):
    """Approve a pending review (HTTP)."""
    coordinator = get_human_review_coordinator()
    result = await coordinator.resume_after_review(
        session_id,
        decision=HumanReviewDecision.APPROVE,
        admin_id="http_admin",
    )

    return {
        "status": "success",
        "session_id": session_id,
        "result": result,
    }


@router.post("/api/admin/reviews/{session_id}/reject")
async def reject_review(
    session_id: str,
    # admin_user = Depends(require_admin_user)
):
    """Reject a pending review (HTTP)."""
    coordinator = get_human_review_coordinator()
    result = await coordinator.resume_after_review(
        session_id,
        decision=HumanReviewDecision.REJECT,
        admin_id="http_admin",
    )

    return {
        "status": "success",
        "session_id": session_id,
        "result": result,
    }


@router.post("/api/admin/reviews/{session_id}/modify")
async def modify_review(
    session_id: str,
    payload: Dict[str, str],
    # admin_user = Depends(require_admin_user)
):
    """
    Modify and approve a pending review (HTTP).
    Body:
        {"modified_content": "..."}
    """
    coordinator = get_human_review_coordinator()

    modified_content = payload.get("modified_content")
    if not modified_content:
        return {"error": "modified_content is required"}, 400

    result = await coordinator.resume_after_review(
        session_id,
        decision=HumanReviewDecision.MODIFY,
        modified_content=modified_content,
        admin_id="http_admin",
    )

    return {
        "status": "success",
        "session_id": session_id,
        "result": result,
    }
