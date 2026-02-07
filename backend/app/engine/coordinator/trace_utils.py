from __future__ import annotations

from typing import Any, Dict, Optional


def build_trace_event(
    node: str,
    status: str = "ok",
    source: Optional[str] = None,
    latency_ms: Optional[float] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    event = {
        "node": node,
        "status": status,
    }
    if source is not None:
        event["source"] = source
    if latency_ms is not None:
        event["latency_ms"] = latency_ms
    if detail:
        event["detail"] = detail
    return event
