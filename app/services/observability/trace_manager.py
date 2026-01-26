"""
Trace manager for storing and persisting decision traces.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.schemas.trace import AgentDecision, CallType, ContextManifest, KnowledgeEvidence, SecurityEvent, TurnTrace

logger = logging.getLogger(__name__)
settings = get_settings()


class TraceManager:
    """In-memory trace registry with SQLite persistence."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        self._traces: dict[str, TurnTrace] = {}
        self._db_path = db_path or settings.TRACE_DB_PATH
        self._init_db()
        self._cleanup_old_traces()

    def _init_db(self) -> None:
        db_file = Path(self._db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    path_taken TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_detail TEXT,
                    ttfs_ms REAL,
                    total_latency_ms REAL,
                    linked_slow_trace_id TEXT,
                    slow_total_ms REAL,
                    timestamp TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_session ON traces (session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_turn ON traces (turn_number)")
            conn.commit()

    def _cleanup_old_traces(self) -> None:
        retention_days = settings.TRACE_RETENTION_DAYS
        if retention_days <= 0:
            return
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("DELETE FROM traces WHERE timestamp < ?", (cutoff.isoformat(),))
                conn.commit()
        except Exception as exc:
            logger.warning("Failed to cleanup traces: %s", exc)

    def start_trace(self, session_id: str, turn_number: int, path_taken: CallType) -> str:
        trace_id = str(uuid.uuid4())
        trace = TurnTrace(
            trace_id=trace_id,
            session_id=session_id,
            turn_number=turn_number,
            path_taken=path_taken,
            timestamp=datetime.utcnow(),
        )
        with self._lock:
            self._traces[trace_id] = trace
        self._persist_trace(trace)
        return trace_id

    def get_trace(self, trace_id: str) -> Optional[TurnTrace]:
        with self._lock:
            trace = self._traces.get(trace_id)
        if trace:
            return trace
        return self._load_trace_from_db(trace_id)

    def record_agent_call(self, trace_id: str, decision: AgentDecision) -> None:
        trace = self.get_trace(trace_id)
        if not trace:
            return
        trace.decisions.append(decision)
        self._persist_trace(trace)

    def record_security_event(self, trace_id: str, event: SecurityEvent) -> None:
        trace = self.get_trace(trace_id)
        if not trace:
            return
        trace.security_events.append(event)
        self._persist_trace(trace)

    def record_evidence(self, trace_id: str, evidence: KnowledgeEvidence) -> None:
        trace = self.get_trace(trace_id)
        if not trace:
            return
        trace.evidences.append(evidence)
        self._persist_trace(trace)

    def set_context_usage(self, trace_id: str, manifest: ContextManifest) -> None:
        trace = self.get_trace(trace_id)
        if not trace:
            return
        trace.context_manifest = manifest
        self._persist_trace(trace)

    def complete_trace(self, trace_id: str, status: str = "success", error: Optional[str] = None) -> None:
        trace = self.get_trace(trace_id)
        if not trace:
            return
        trace.status = status
        trace.error_detail = error
        self._persist_trace(trace)

    def link_slow_path(self, fast_trace_id: str, slow_trace_id: str, slow_total_ms: float) -> None:
        trace = self.get_trace(fast_trace_id)
        if not trace:
            return
        trace.linked_slow_trace_id = slow_trace_id
        trace.slow_total_ms = slow_total_ms
        self._persist_trace(trace)

    def _serialize_trace(self, trace: TurnTrace) -> str:
        data = trace.model_dump()
        data["path_taken"] = trace.path_taken.value
        data["timestamp"] = trace.timestamp.isoformat()
        return json.dumps(data, ensure_ascii=True, default=str)

    def _persist_trace(self, trace: TurnTrace) -> None:
        payload = self._serialize_trace(trace)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO traces (
                    trace_id,
                    session_id,
                    turn_number,
                    path_taken,
                    status,
                    error_detail,
                    ttfs_ms,
                    total_latency_ms,
                    linked_slow_trace_id,
                    slow_total_ms,
                    timestamp,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trace_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    turn_number=excluded.turn_number,
                    path_taken=excluded.path_taken,
                    status=excluded.status,
                    error_detail=excluded.error_detail,
                    ttfs_ms=excluded.ttfs_ms,
                    total_latency_ms=excluded.total_latency_ms,
                    linked_slow_trace_id=excluded.linked_slow_trace_id,
                    slow_total_ms=excluded.slow_total_ms,
                    timestamp=excluded.timestamp,
                    data_json=excluded.data_json
                """,
                (
                    trace.trace_id,
                    trace.session_id,
                    trace.turn_number,
                    trace.path_taken.value,
                    trace.status,
                    trace.error_detail,
                    trace.ttfs_ms,
                    trace.total_latency_ms,
                    trace.linked_slow_trace_id,
                    trace.slow_total_ms,
                    trace.timestamp.isoformat(),
                    payload,
                ),
            )
            conn.commit()

    def _load_trace_from_db(self, trace_id: str) -> Optional[TurnTrace]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT data_json FROM traces WHERE trace_id = ?",
                    (trace_id,),
                ).fetchone()
                if not row:
                    return None
                data = json.loads(row[0])
                trace = TurnTrace.model_validate(data)
                with self._lock:
                    self._traces[trace_id] = trace
                return trace
        except Exception as exc:
            logger.warning("Failed to load trace %s: %s", trace_id, exc)
            return None


trace_manager = TraceManager()
