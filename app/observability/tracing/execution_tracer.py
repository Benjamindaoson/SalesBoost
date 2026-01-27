import logging
import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Trace(BaseModel):
    trace_id: str
    session_id: str
    user_id: str
    start_time: float
    end_time: Optional[float] = None
    steps: List[Dict[str, Any]] = []
    agent_calls: List[Any] = [] # Added for script
    error: Optional[str] = None

class ExecutionTracer:
    """
    Observability Tracer for Agentic Workflows.
    Records steps, tokens, and latency.
    """
    
    def __init__(self):
        self._active_traces: Dict[str, Trace] = {}
        self._completed_traces: Dict[str, Trace] = {} # Added for get_trace

    def start_trace(self, trace_id: str, session_id: str, user_id: str):
        logger.info(f"Starting trace: {trace_id}")
        self._active_traces[trace_id] = Trace(
            trace_id=trace_id,
            session_id=session_id,
            user_id=user_id,
            start_time=time.time()
        )

    def record_agent_call(self, trace_id: str, decision: Any):
        if trace_id in self._active_traces:
            self._active_traces[trace_id].agent_calls.append(decision)

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self._completed_traces.get(trace_id) or self._active_traces.get(trace_id)

    def record_step(self, trace_id: str, step_name: str, data: Dict[str, Any]):
        if trace_id in self._active_traces:
            self._active_traces[trace_id].steps.append({
                "name": step_name,
                "timestamp": time.time(),
                "data": data
            })

    def complete_trace(self, trace_id: str, error: Optional[str] = None):
        if trace_id in self._active_traces:
            trace = self._active_traces.pop(trace_id)
            trace.end_time = time.time()
            trace.error = error
            duration = (trace.end_time - trace.start_time) * 1000
            logger.info(f"Completed trace: {trace_id} in {duration:.2f}ms")
            self._completed_traces[trace_id] = trace

trace_manager = ExecutionTracer()
