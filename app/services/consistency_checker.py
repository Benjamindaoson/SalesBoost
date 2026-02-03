import asyncio
import logging
from typing import Any
from app.infra.events.bus import bus
from app.infra.events.schemas import EventType, EvaluationEventPayload
from app.observability.tracing.execution_tracer import trace_manager

logger = logging.getLogger(__name__)

# Logic Consistency Simulation
# In real system, this calls LLM with retry prompt

@bus.subscribe(EventType.EVALUATION_COMPLETED)
async def check_consistency(payload: Any):
    if isinstance(payload, dict):
        payload = EvaluationEventPayload(**payload)
        
    logger.info(f"Checking consistency for evaluation {payload.evaluation_id}")
    
    # Logic: If score is high but comments are negative -> Inconsistent
    is_consistent = True
    correction_needed = ""
    
    if payload.score > 8.0 and "bad" in payload.comments.lower():
        is_consistent = False
        correction_needed = "Score is high (>8) but comments mention 'bad'. Please align score with comments."
    
    if not is_consistent:
        logger.warning(f"Consistency check failed: {correction_needed}")
        trace_manager.record_metric("consistency_check_failed", 1.0, {"evaluation_id": payload.evaluation_id})
        
        # Trigger Retry
        if payload.retry_count < 3:
            retry_payload = payload.model_copy()
            retry_payload.retry_count += 1
            retry_payload.correction_prompt = correction_needed
            retry_payload.event_id = f"{payload.event_id}_retry_{payload.retry_count}"
            
            logger.info(f"Publishing RETRY_EVALUATION attempt {retry_payload.retry_count}")
            trace_manager.record_metric("evaluation_retry_triggered", 1.0, {"retry_count": str(retry_payload.retry_count)})
            
            await bus.publish(EventType.RETRY_EVALUATION, retry_payload)
        else:
            logger.error("Max retries reached for consistency check.")
            trace_manager.record_metric("evaluation_max_retries_reached", 1.0, {"evaluation_id": payload.evaluation_id})
    else:
        logger.info("Consistency check passed.")
        trace_manager.record_metric("consistency_check_passed", 1.0, {"evaluation_id": payload.evaluation_id})

@bus.subscribe(EventType.RETRY_EVALUATION)
async def handle_retry(payload: Any):
    if isinstance(payload, dict):
        payload = EvaluationEventPayload(**payload)
    
    logger.info(f"Processing retry for {payload.evaluation_id} with prompt: {payload.correction_prompt}")
    
    # Simulate LLM correction
    await asyncio.sleep(0.2)
    
    # Simulate corrected result
    new_score = 4.0 # Lowered score to match "bad"
    new_comments = payload.comments
    
    # Publish completion again
    new_payload = payload.model_copy()
    new_payload.score = new_score
    new_payload.event_id = f"{payload.event_id}_corrected"
    
    await bus.publish(EventType.EVALUATION_COMPLETED, new_payload)
