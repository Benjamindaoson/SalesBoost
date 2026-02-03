"""
Celery Tasks for Asynchronous Coach Advice Generation
Enables background processing and WebSocket push notifications
"""
from celery import Celery, Task
from typing import Dict, Any, Optional
import logging
import json

from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    'salesboost_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


class CoachAdviceTask(Task):
    """Base task for coach advice generation"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(
            f"[CoachAdviceTask] Task {task_id} failed: {exc}",
            exc_info=einfo
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"[CoachAdviceTask] Task {task_id} completed successfully")


@celery_app.task(
    base=CoachAdviceTask,
    name='tasks.generate_coach_advice_async',
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def generate_coach_advice_async(
    self,
    session_id: str,
    turn_number: int,
    user_message: str,
    npc_response: str,
    history: list,
    intent: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate coach advice asynchronously

    This task:
    1. Generates coach advice in the background
    2. Pushes result to WebSocket
    3. Stores result in Redis for retrieval

    Args:
        session_id: Session ID
        turn_number: Turn number
        user_message: User input
        npc_response: NPC response
        history: Conversation history
        intent: Detected intent

    Returns:
        Dict with advice and metadata
    """
    try:
        from app.agents.ask.coach_agent import SalesCoachAgent
        from app.engine.coordinator.dynamic_workflow import FALLBACK_COACH_ADVICE
        import asyncio

        logger.info(
            f"[CoachAdviceTask] Generating advice for session={session_id}, "
            f"turn={turn_number}"
        )

        # Initialize coach agent
        coach_agent = SalesCoachAgent()

        # Generate advice (run async function in sync context)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            advice_obj = loop.run_until_complete(
                coach_agent.get_advice(
                    history=history + [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": npc_response}
                    ],
                    session_id=session_id,
                    turn_number=turn_number
                )
            )
        finally:
            loop.close()

        # Handle result
        if advice_obj and advice_obj.advice:
            advice_text = advice_obj.advice
            advice_source = "ai"
        else:
            # Fallback
            fallback_entry = FALLBACK_COACH_ADVICE.get(
                intent or "default",
                FALLBACK_COACH_ADVICE["error_fallback"]
            )
            advice_text = fallback_entry["advice"]
            advice_tips = fallback_entry.get("tips", [])

            if advice_tips:
                advice_text = f"{advice_text}\n\n💡 关键提示：\n" + "\n".join(
                    f"  • {tip}" for tip in advice_tips
                )

            advice_source = "fallback"

        result = {
            "session_id": session_id,
            "turn_number": turn_number,
            "advice": advice_text,
            "source": advice_source,
            "intent": intent
        }

        # Store in Redis
        try:
            from core.redis import get_redis_sync
            redis_client = get_redis_sync()

            advice_key = f"coach_advice:{session_id}:{turn_number}"
            redis_client.setex(
                advice_key,
                3600,  # 1 hour TTL
                json.dumps(result)
            )
        except Exception as e:
            logger.warning(f"[CoachAdviceTask] Failed to store in Redis: {e}")

        # Push to WebSocket
        try:
            push_coach_advice_to_websocket.delay(session_id, result)
        except Exception as e:
            logger.warning(f"[CoachAdviceTask] Failed to push to WebSocket: {e}")

        logger.info(
            f"[CoachAdviceTask] Advice generated: session={session_id}, "
            f"source={advice_source}"
        )

        return result

    except Exception as exc:
        logger.error(
            f"[CoachAdviceTask] Failed to generate advice: {exc}",
            exc_info=True
        )

        # Retry with exponential backoff
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.push_coach_advice_to_websocket',
    bind=True,
    max_retries=3
)
def push_coach_advice_to_websocket(
    self,
    session_id: str,
    advice_data: Dict[str, Any]
):
    """
    Push coach advice to WebSocket

    Args:
        session_id: Session ID
        advice_data: Advice data to push
    """
    try:
        from app.infra.websocket.manager import get_websocket_manager

        manager = get_websocket_manager()

        # Send to WebSocket
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                manager.send_coach_advice(session_id, advice_data)
            )
        finally:
            loop.close()

        logger.info(f"[WebSocketPush] Advice pushed to session={session_id}")

    except Exception as exc:
        logger.error(
            f"[WebSocketPush] Failed to push advice: {exc}",
            exc_info=True
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.batch_generate_coach_advice',
    bind=True
)
def batch_generate_coach_advice(
    self,
    tasks: list[Dict[str, Any]]
):
    """
    Batch generate coach advice for multiple turns

    Useful for:
    - Backfilling historical conversations
    - Bulk processing

    Args:
        tasks: List of task parameters
    """
    results = []

    for task_params in tasks:
        try:
            result = generate_coach_advice_async.apply_async(
                kwargs=task_params,
                countdown=0
            )
            results.append({
                "task_id": result.id,
                "session_id": task_params.get("session_id"),
                "status": "queued"
            })
        except Exception as e:
            results.append({
                "session_id": task_params.get("session_id"),
                "status": "failed",
                "error": str(e)
            })

    return {
        "total": len(tasks),
        "queued": sum(1 for r in results if r.get("status") == "queued"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "results": results
    }


# ==================== Helper Functions ====================

def trigger_async_coach_advice(
    session_id: str,
    turn_number: int,
    user_message: str,
    npc_response: str,
    history: list,
    intent: Optional[str] = None,
    countdown: int = 0
) -> str:
    """
    Trigger asynchronous coach advice generation

    Args:
        session_id: Session ID
        turn_number: Turn number
        user_message: User input
        npc_response: NPC response
        history: Conversation history
        intent: Detected intent
        countdown: Delay before execution (seconds)

    Returns:
        Task ID
    """
    result = generate_coach_advice_async.apply_async(
        kwargs={
            "session_id": session_id,
            "turn_number": turn_number,
            "user_message": user_message,
            "npc_response": npc_response,
            "history": history,
            "intent": intent
        },
        countdown=countdown
    )

    logger.info(
        f"[AsyncCoach] Task queued: task_id={result.id}, "
        f"session={session_id}, turn={turn_number}"
    )

    return result.id


def get_coach_advice_result(task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    Get coach advice result from task

    Args:
        task_id: Celery task ID
        timeout: Timeout in seconds

    Returns:
        Advice data or None if not ready
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    try:
        if result.ready():
            return result.get(timeout=timeout)
        else:
            return None
    except Exception as e:
        logger.error(f"[AsyncCoach] Failed to get result: {e}")
        return None
