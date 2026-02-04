"""
User Feedback API Endpoint
Collects user satisfaction ratings and feeds them to the Bandit algorithm
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, conint
from typing import Optional, Dict
import logging

from app.engine.coordinator.production_coordinator import get_production_coordinator
from app.observability.coordinator_metrics import record_user_feedback
from core.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class UserFeedbackRequest(BaseModel):
    """User feedback submission"""
    session_id: str = Field(..., description="Session ID")
    turn_number: int = Field(..., ge=1, description="Turn number")
    rating: conint(ge=1, le=5) = Field(..., description="User satisfaction rating (1-5)")
    intent: Optional[str] = Field(None, description="Intent of the turn")
    comment: Optional[str] = Field(None, max_length=500, description="Optional comment")

    # Bandit-specific fields
    decision_id: Optional[str] = Field(None, description="Bandit decision ID to reward")

    # Additional signals for multi-objective optimization
    signals: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Additional feedback signals (e.g., response_quality, latency_satisfaction)"
    )


class UserFeedbackResponse(BaseModel):
    """Feedback submission response"""
    success: bool
    message: str
    bandit_updated: bool = False
    reward_recorded: float = 0.0


def rating_to_reward(rating: int) -> float:
    """
    Convert 1-5 star rating to -1 to 1 reward signal

    Mapping:
    - 5 stars -> +1.0 (excellent)
    - 4 stars -> +0.5 (good)
    - 3 stars -> 0.0 (neutral)
    - 2 stars -> -0.5 (poor)
    - 1 star -> -1.0 (terrible)
    """
    mapping = {
        5: 1.0,
        4: 0.5,
        3: 0.0,
        2: -0.5,
        1: -1.0
    }
    return mapping.get(rating, 0.0)


@router.post("/submit", response_model=UserFeedbackResponse)
async def submit_feedback(
    feedback: UserFeedbackRequest,
    redis_client = Depends(get_redis)
):
    """
    Submit user feedback for a conversation turn

    This endpoint:
    1. Records the feedback in metrics (Prometheus)
    2. Stores feedback in Redis for analysis
    3. Sends reward signal to Bandit algorithm (if decision_id provided)

    Example:
        POST /api/v1/feedback/submit
        {
            "session_id": "abc123",
            "turn_number": 3,
            "rating": 5,
            "intent": "price_inquiry",
            "decision_id": "bandit_decision_xyz",
            "signals": {
                "response_quality": 0.9,
                "latency_satisfaction": 0.8
            }
        }
    """
    try:
        # 1. Record metrics
        record_user_feedback(
            rating=feedback.rating,
            intent=feedback.intent or "unknown"
        )

        # 2. Store feedback in Redis
        feedback_key = f"feedback:{feedback.session_id}:{feedback.turn_number}"
        feedback_data = feedback.model_dump()

        try:
            await redis_client.setex(
                feedback_key,
                86400 * 7,  # Keep for 7 days
                str(feedback_data)
            )
        except Exception as e:
            logger.warning(f"Failed to store feedback in Redis: {e}")

        # 3. Send reward to Bandit (if decision_id provided)
        bandit_updated = False
        reward = rating_to_reward(feedback.rating)

        if feedback.decision_id:
            try:
                # Get coordinator (this is a simplified approach)
                # In production, you'd want to maintain coordinator instances per session
                from app.infra.gateway.model_gateway import ModelGateway
                from app.infra.budget.budget_manager import BudgetManager

                coordinator = get_production_coordinator(
                    model_gateway=ModelGateway(),
                    budget_manager=BudgetManager(),
                    persona={}
                )

                # Record bandit feedback
                bandit_updated = await coordinator.record_bandit_feedback(
                    decision_id=feedback.decision_id,
                    reward=reward,
                    signals=feedback.signals
                )

                if bandit_updated:
                    logger.info(
                        f"Bandit feedback recorded: decision_id={feedback.decision_id}, "
                        f"reward={reward}, rating={feedback.rating}"
                    )

            except Exception as e:
                logger.error(f"Failed to update bandit: {e}", exc_info=True)

        return UserFeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
            bandit_updated=bandit_updated,
            reward_recorded=reward
        )

    except Exception as e:
        logger.error(f"Failed to process feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process feedback: {str(e)}"
        )


@router.get("/stats/{session_id}")
async def get_session_feedback_stats(
    session_id: str,
    redis_client = Depends(get_redis)
):
    """
    Get feedback statistics for a session

    Returns:
        - Average rating
        - Total feedback count
        - Rating distribution
    """
    try:
        # Scan for all feedback keys for this session
        pattern = f"feedback:{session_id}:*"
        keys = []

        try:
            cursor = 0
            while True:
                cursor, batch = await redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                keys.extend(batch)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Failed to scan Redis: {e}")
            return {
                "session_id": session_id,
                "total_feedback": 0,
                "average_rating": 0.0,
                "rating_distribution": {}
            }

        if not keys:
            return {
                "session_id": session_id,
                "total_feedback": 0,
                "average_rating": 0.0,
                "rating_distribution": {}
            }

        # Fetch all feedback
        ratings = []
        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for key in keys:
            try:
                data = await redis_client.get(key)
                if data:
                    import ast
                    feedback_dict = ast.literal_eval(data)
                    rating = feedback_dict.get("rating")
                    if rating:
                        ratings.append(rating)
                        rating_counts[rating] = rating_counts.get(rating, 0) + 1
            except Exception as e:
                logger.warning(f"Failed to parse feedback: {e}")

        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

        return {
            "session_id": session_id,
            "total_feedback": len(ratings),
            "average_rating": round(avg_rating, 2),
            "rating_distribution": rating_counts
        }

    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback stats: {str(e)}"
        )


@router.post("/batch-submit")
async def submit_batch_feedback(
    feedbacks: list[UserFeedbackRequest],
    redis_client = Depends(get_redis)
):
    """
    Submit multiple feedback entries at once

    Useful for:
    - End-of-conversation bulk feedback
    - Offline feedback collection
    """
    results = []

    for feedback in feedbacks:
        try:
            result = await submit_feedback(feedback, redis_client)
            results.append({
                "session_id": feedback.session_id,
                "turn_number": feedback.turn_number,
                "success": result.success
            })
        except Exception as e:
            results.append({
                "session_id": feedback.session_id,
                "turn_number": feedback.turn_number,
                "success": False,
                "error": str(e)
            })

    success_count = sum(1 for r in results if r.get("success"))

    return {
        "total": len(feedbacks),
        "success": success_count,
        "failed": len(feedbacks) - success_count,
        "results": results
    }
