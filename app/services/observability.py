import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.schemas.trace import TurnTrace, AgentDecision, SecurityEvent, KnowledgeEvidence, ContextManifest, CallType

logger = logging.getLogger(__name__)

class TraceManager:
    """
    V3 可观测性管理器
    负责收集、聚合和检索全链路追踪数据
    """
    def __init__(self):
        self._traces: Dict[str, TurnTrace] = {} # trace_id -> TurnTrace
        self._session_map: Dict[str, List[str]] = {} # session_id -> [trace_ids]

    # ... (existing methods)

    def set_context_manifest(self, trace_id: str, manifest: ContextManifest):
        if trace_id in self._traces:
            self._traces[trace_id].context_manifest = manifest

    def get_trace_replay(self, trace_id: str) -> Dict[str, Any]:
        """结构化回放接口"""
        trace = self._traces.get(trace_id)
        if not trace:
            return {"error": "Trace not found"}
            
        context_data = {}
        if trace.context_manifest:
            context_data = {
                "total_tokens": trace.context_manifest.total_tokens,
                "summary": trace.context_manifest.manifest_summary,
                "layers": [
                    {
                        "name": l.name,
                        "source": l.source,
                        "tokens": l.tokens,
                        "truncated": l.truncated,
                        "reason": l.truncation_reason
                    }
                    for l in trace.context_manifest.layers
                ]
            }

        return {
            "trace_id": trace.trace_id,
            "turn": trace.turn_number,
            "path": trace.path_taken.value,
            "ttfs_ms": trace.ttfs_ms,
            "ttfs_stop_point": trace.ttfs_stop_point,
            "total_latency_ms": trace.total_latency_ms,
            "linked_slow_trace_id": trace.linked_slow_trace_id,
            "slow_total_ms": trace.slow_total_ms,
            "decisions": [
                {
                    "agent": d.agent_name,
                    "action": d.action,
                    "provider": getattr(d, "provider", None),
                    "model": getattr(d, "model_used", None),
                    "latency": f"{d.latency_ms:.2f}ms",
                    "reasoning": getattr(d, "reasoning", None),
                    "routing_reason": getattr(d, "routing_reason", None),
                    "downgrade_reason": getattr(d, "downgrade_reason", None),
                    "budget_remaining": getattr(d, "budget_remaining", None),
                } for d in trace.decisions
            ],
            "context_manifest": context_data,
            "security_events": [
                {
                    "type": e.event_type,
                    "action": e.action_taken,
                    "rule": e.rule_id,
                    "trigger_point": e.trigger_point,
                    "reason": e.reason
                }
                for e in trace.security_events
            ],
            "evidence_pack": [
                {
                    "evidence_id": e.evidence_id,
                    "source": e.source,
                    "confidence": e.confidence,
                    "metadata": e.metadata,
                }
                for e in trace.evidences
            ]
        }
    def start_trace(self, session_id: str, turn_number: int, path: CallType) -> str:
        trace_id = f"tr-{uuid.uuid4().hex[:8]}"
        trace = TurnTrace(
            trace_id=trace_id,
            session_id=session_id,
            turn_number=turn_number,
            path_taken=path
        )
        self._traces[trace_id] = trace
        if session_id not in self._session_map:
            self._session_map[session_id] = []
        self._session_map[session_id].append(trace_id)
        return trace_id

    def record_agent_call(self, trace_id: str, decision: AgentDecision):
        if trace_id in self._traces:
            self._traces[trace_id].decisions.append(decision)
            # 自动累加总延迟
            self._traces[trace_id].total_latency_ms += decision.latency_ms

    def record_security_event(self, trace_id: str, event: SecurityEvent):
        if trace_id in self._traces:
            self._traces[trace_id].security_events.append(event)
            if event.action_taken in ["block", "reject"]:
                self._traces[trace_id].status = "blocked"

    def record_evidence(self, trace_id: str, evidence: KnowledgeEvidence):
        if trace_id in self._traces:
            self._traces[trace_id].evidences.append(evidence)

    def set_context_usage(self, trace_id: str, usage: ContextManifest):
        if trace_id in self._traces:
            self._traces[trace_id].context_manifest = usage

    def complete_trace(self, trace_id: str, status: str = "success", error: Optional[str] = None):
        if trace_id in self._traces:
            trace = self._traces[trace_id]
            trace.status = status
            trace.error_detail = error
            logger.info(f"Trace {trace_id} completed: {status} | Path: {trace.path_taken} | Latency: {trace.total_latency_ms:.2f}ms")

    def link_slow_path(self, fast_trace_id: str, slow_trace_id: str, slow_total_ms: float):
        if fast_trace_id in self._traces:
            self._traces[fast_trace_id].linked_slow_trace_id = slow_trace_id
            self._traces[fast_trace_id].slow_total_ms = slow_total_ms

    def get_trace(self, trace_id: str) -> Optional[TurnTrace]:
        return self._traces.get(trace_id)

    def get_session_history(self, session_id: str) -> List[TurnTrace]:
        trace_ids = self._session_map.get(session_id, [])
        return [self._traces[tid] for tid in trace_ids if tid in self._traces]

    def export_metrics(self) -> Dict[str, Any]:
        """导出全量指标概览"""
        all_traces = list(self._traces.values())
        if not all_traces:
            return {}
        
        return {
            "total_turns": len(all_traces),
            "avg_latency": sum(t.total_latency_ms for t in all_traces) / len(all_traces),
            "total_cost": sum(sum(d.estimated_cost for d in t.decisions) for t in all_traces),
            "path_distribution": {
                "fast": len([t for t in all_traces if t.path_taken == CallType.FAST_PATH]),
                "slow": len([t for t in all_traces if t.path_taken == CallType.SLOW_PATH])
            },
            "security_incidents": sum(len(t.security_events) for t in all_traces)
        }

# 单例
trace_manager = TraceManager()
