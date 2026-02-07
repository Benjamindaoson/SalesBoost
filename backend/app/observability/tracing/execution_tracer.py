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

    def start_trace(self, trace_id: str, session_id: str = "global", user_id: str = "system"):
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

    def complete_trace(self, trace_id: str, error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        if trace_id in self._active_traces:
            trace = self._active_traces.pop(trace_id)
            trace.end_time = time.time()
            trace.error = error
            if metadata:
                trace.steps.append({"name": "completion_metadata", "data": metadata, "timestamp": time.time()})
            duration = (trace.end_time - trace.start_time) * 1000
            
            logger.info(f"Completed trace: {trace_id} in {duration:.2f}ms")
            
            # Persist to JSONL file (Simulating DB write for durability)
            self._persist_trace(trace)
            self._completed_traces[trace_id] = trace # Keep recent history for debug

    def record_metric(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """
        Record a custom metric (counter, gauge, etc.)
        In prod, this would send to Prometheus/StatsD
        """
        tags_str = ",".join([f"{k}={v}" for k,v in (tags or {}).items()])
        logger.info(f"[METRIC] {name}={value} {tags_str}")
        # Could also write to a metrics.jsonl file


    def _persist_trace(self, trace: Trace):
        import json
        from pathlib import Path
        
        # Use a local file for audit durability test if DB not ready
        # In prod this would be: await db.add(TraceModel(**trace.dict()))
        trace_file = Path("storage/traces.jsonl")
        trace_file.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace.model_dump(), default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist trace {trace.trace_id}: {e}")

trace_manager = ExecutionTracer()
