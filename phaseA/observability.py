from typing import Dict
import time

class TraceLogger:
    def __init__(self):
        self.records = []
    def log(self, trace_id: str, span: str, metrics: Dict[str, float]):
        self.records.append({"trace_id": trace_id, "span": span, "metrics": metrics, "ts": time.time()})
    def get_recent(self, limit: int = 10):
        return self.records[-limit:]

def log_trace(trace_logger: TraceLogger, trace_id: str, span: str, metrics: Dict[str, float]):
    trace_logger.log(trace_id, span, metrics)
