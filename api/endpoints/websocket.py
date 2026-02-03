"""
WebSocket endpoint for training sessions (V3).
"""

import asyncio
import hashlib
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_db_session
from api.deps import require_user
from api.auth_schemas import UserSchema as User
from api.deps import get_current_user_from_token
from models.config_models import Course, CustomerPersona, ScenarioConfig
from models.runtime_models import Message, Session, SessionState
from schemas.fsm import FSMState, SalesStage
from app.engine.state.recovery import state_recovery_service
from app.cognitive.errors import AuditBlockedError, CognitiveError, TimeoutError as CognitiveTimeoutError
from app.engine.coordinator.production_coordinator import ProductionCoordinator, get_production_coordinator
from app.infra.gateway.model_gateway import ModelGateway
from app.observability.metrics.business_metrics import performance_metrics_collector

from app.infra.gateway.budget import BudgetManager

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.orchestrators: dict[str, ProductionCoordinator] = {}
        self.pending_events: dict[str, dict[str, set[int]]] = {}
        self.unacked_chunks: dict[str, dict[int, dict]] = {} # session_id -> {seq_id: chunk_data}
        self.recovery_enabled = True
        self._retry_task: Optional[asyncio.Task] = None
        self.turn_guard: dict[str, dict[str, float]] = {}

    async def connect(
        self, websocket: WebSocket, session_id: str, user_id: str = "default_user"
    ) -> Optional[dict]:
        self.active_connections[session_id] = websocket
        self.pending_events[session_id] = {}
        self.unacked_chunks[session_id] = {}
        
        # Start global retransmission task once
        if self._retry_task is None or self._retry_task.done():
            self._retry_task = asyncio.create_task(self._retransmission_loop())

        # 灏濊瘯鎭㈠鐘舵€?
        recovery_info = None
        if self.recovery_enabled and user_id:
            try:
                recovery_info = await state_recovery_service.recover_session_state(session_id, user_id)
                if recovery_info:
                    # 鎭㈠缂栨帓鍣?
                    self.orchestrators[session_id] = recovery_info["orchestrator"]
                    logger.info("Session state recovered: %s", session_id)
            except Exception as e:
                logger.error("State recovery failed for session %s: %s", session_id, e)

        logger.info("WebSocket connected: %s", session_id)
        return recovery_info

    async def disconnect(self, session_id: str, user_id: str = None) -> None:
        # 鍒涘缓鐘舵€佸揩鐓?
        if self.recovery_enabled and user_id and session_id in self.orchestrators:
            try:
                coordinator = self.orchestrators[session_id]
                current_stage = getattr(getattr(coordinator, "fsm_state", None), "current_stage", None)
                stage_value = current_stage.value if current_stage else "unknown"
                context = {
                    "history": getattr(coordinator, "history", []),
                    "fsm_state": getattr(coordinator, "fsm_state", None),
                }
                await state_recovery_service.create_recovery_checkpoint(
                    session_id=session_id,
                    user_id=user_id,
                    current_stage=stage_value,
                    context=context,
                )
                logger.info("State snapshot created for session: %s", session_id)
            except Exception as e:
                logger.error("Failed to create state snapshot for session %s: %s", session_id, e)

        self.active_connections.pop(session_id, None)
        self.orchestrators.pop(session_id, None)
        self.pending_events.pop(session_id, None)
        self.unacked_chunks.pop(session_id, None)
        self.turn_guard.pop(session_id, None)
        if not self.active_connections and self._retry_task:
            self._retry_task.cancel()
            self._retry_task = None
        logger.info("WebSocket disconnected: %s", session_id)

    async def send_json(self, session_id: str, data: dict) -> None:
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

    async def send_chunk(self, session_id: str, chunk: dict) -> None:
        """Send chunk with sequence ID and track for ACK."""
        seq_id = chunk.get("sequence")
        if seq_id is not None:
            self.unacked_chunks.setdefault(session_id, {})[seq_id] = {
                "data": chunk,
                "sent_at": time.time(),
                "retries": 0
            }
        await self.send_json(session_id, chunk)

    async def ack_chunk(self, session_id: str, seq_id: int) -> None:
        if session_id in self.unacked_chunks:
            self.unacked_chunks[session_id].pop(seq_id, None)

    async def _retransmission_loop(self):
        """Background task for retransmission with exponential backoff."""
        try:
            while self.active_connections:
                await asyncio.sleep(2.0) # Check every 2 seconds
                now = time.time()
                for session_id, chunks in list(self.unacked_chunks.items()):
                    if session_id not in self.active_connections:
                        continue
                    to_retry = []
                    for seq_id, info in chunks.items():
                        # Exponential backoff: 2, 4, 8, 16...
                        wait_time = 2.0 * (2 ** info["retries"])
                        if now - info["sent_at"] > wait_time:
                            to_retry.append((seq_id, info))
                    for seq_id, info in to_retry:
                        if info["retries"] > 5: # Max retries
                            logger.warning("Max retries reached for session %s, seq %s", session_id, seq_id)
                            self.unacked_chunks[session_id].pop(seq_id, None)
                            continue
                        logger.info(
                            "Retransmitting chunk %s for session %s (retry %s)",
                            seq_id,
                            session_id,
                            info["retries"] + 1,
                        )
                        info["retries"] += 1
                        info["sent_at"] = now
                        await self.send_json(session_id, info["data"])
        finally:
            self._retry_task = None

    def set_orchestrator(self, session_id: str, orchestrator: ProductionCoordinator) -> None:
        self.orchestrators[session_id] = orchestrator

    def get_orchestrator(self, session_id: str) -> Optional[ProductionCoordinator]:
        return self.orchestrators.get(session_id)

    def get_db(self, session_id: str) -> Optional[AsyncSession]:
        return None

    def register_stream(self, session_id: str, event_id: str, total_chunks: int) -> None:
        self.pending_events.setdefault(session_id, {})[event_id] = set()
        logger.info("Stream registered: %s chunks=%s", event_id, total_chunks)

    def ack_stream(self, session_id: str, event_id: str, sequence: int) -> None:
        if session_id in self.pending_events and event_id in self.pending_events[session_id]:
            self.pending_events[session_id][event_id].add(sequence)

    def is_duplicate_turn(self, session_id: str, turn_id: str, ttl_seconds: int = 300) -> bool:
        now = time.time()
        guard = self.turn_guard.setdefault(session_id, {})
        expired = [tid for tid, ts in guard.items() if now - ts > ttl_seconds]
        for tid in expired:
            guard.pop(tid, None)
        return turn_id in guard

    def mark_turn_seen(self, session_id: str, turn_id: str) -> None:
        self.turn_guard.setdefault(session_id, {})[turn_id] = time.time()

    def clear_turn_seen(self, session_id: str, turn_id: str) -> None:
        if session_id in self.turn_guard:
            self.turn_guard[session_id].pop(turn_id, None)

    async def send_tool_status(self, session_id: str, tool_event: dict) -> None:
        """
        Send tool execution status event to client.

        Args:
            session_id: Session ID
            tool_event: Tool event data containing:
                - tool_name: Name of the tool
                - status: started|completed|failed
                - latency_ms: Execution latency (for completed/failed)
                - result_preview: Preview of result (for completed)
                - error: Error message (for failed)
        """
        event = {
            "event": "tool_status",
            "data": tool_event,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.send_json(session_id, event)



class SimpleModelCaller:
    async def generate(self, prompt: str, context: dict) -> str:
        history = context.get("history", [])
        if history:
            raise CognitiveError("SimpleModelCaller must not receive history")
        if context.get("fsm") is not None:
            raise CognitiveError("SimpleModelCaller must not receive FSM")
        if context.get("state") is not None:
            raise CognitiveError("SimpleModelCaller must not receive state")
        stage = context.get("stage", "training")
        return f"[{stage}] {prompt}"

manager = ConnectionManager()


@router.get("/sessions/{user_id}/recoverable")
async def get_recoverable_sessions(user_id: str, current_user: User = Depends(require_user)):
    """鑾峰彇鍙仮澶嶇殑浼氳瘽鍒楄〃"""
    if current_user.role != "admin" and user_id != current_user.id:
        return {"success": False, "error": "Forbidden"}
    try:
        sessions = await state_recovery_service.list_recoverable_sessions(user_id)
        return {"success": True, "data": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error("Failed to get recoverable sessions for user %s: %s", user_id, e)
        return {"success": False, "error": str(e)}


@router.post("/sessions/{session_id}/recover")
async def recover_session(session_id: str, user_id: str, current_user: User = Depends(require_user)):
    """鎭㈠鐗瑰畾浼氳瘽"""
    if current_user.role != "admin" and user_id != current_user.id:
        return {"success": False, "error": "Forbidden"}
    try:
        recovery_info = await state_recovery_service.recover_session_state(session_id, user_id)
        if recovery_info:
            return {"success": True, "data": recovery_info}
        else:
            return {"success": False, "error": "No recoverable session found"}
    except Exception as e:
        logger.error("Failed to recover session %s for user %s: %s", session_id, user_id, e)
        return {"success": False, "error": str(e)}


@router.delete("/sessions/{session_id}/snapshot")
async def delete_session_snapshot(session_id: str, user_id: str, current_user: User = Depends(require_user)):
    """鍒犻櫎浼氳瘽蹇収"""
    if current_user.role != "admin" and user_id != current_user.id:
        return {"success": False, "error": "Forbidden"}
    try:
        success = await state_recovery_service.state_snapshot_service.delete_snapshot(session_id)
        return {
            "success": success,
            "message": "Snapshot deleted successfully" if success else "Failed to delete snapshot",
        }
    except Exception as e:
        logger.error("Failed to delete snapshot for session %s: %s", session_id, e)
        return {"success": False, "error": str(e)}


@router.websocket("/train")
async def websocket_training(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    scenario_id: Optional[str] = Query(None),
    persona_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    settings = get_settings()
    current_user = None

    if not token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

    if not token:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    async for db in get_db_session():
        try:
            current_user = await get_current_user_from_token(token, db)
        except Exception:
            await websocket.close(code=4401, reason="Unauthorized")
            return
        break

    if not current_user:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    if user_id and current_user.role != "admin" and user_id != current_user.id:
        await websocket.close(code=4403, reason="Forbidden")
        return

    user_id = current_user.id

    try:
        if not session_id:
            if not all([course_id, scenario_id, persona_id, user_id]):
                await websocket.close(code=400, reason="Missing required parameters")
                return
            session_id = str(uuid.uuid4())
            db_session = None
        else:
            async for db in get_db_session():
                session_result = await db.execute(select(Session).where(Session.id == session_id))
                db_session = session_result.scalar_one_or_none()
                if not db_session:
                    await websocket.close(code=404, reason=f"Session not found: {session_id}")
                    return
                if current_user.role != "admin" and db_session.user_id != current_user.id:
                    await websocket.close(code=4403, reason="Forbidden")
                    return
                course_id = db_session.course_id
                scenario_id = db_session.scenario_id
                persona_id = db_session.persona_id
                user_id = db_session.user_id
                break

        await websocket.accept()
        await manager.connect(websocket, session_id, user_id)

        async for db in get_db_session():
            course = await _load_course(db, course_id, session_id)
            scenario_config = await _load_scenario(db, scenario_id, session_id)
            customer_persona = await _load_persona(db, persona_id, session_id)
            break
        if not (course and scenario_config and customer_persona):
            return

        if not db_session:
            async for db in get_db_session():
                db_session = Session(
                    id=session_id,
                    user_id=user_id,
                    course_id=course_id,
                    scenario_id=scenario_id,
                    persona_id=persona_id,
                    status="active",
                    started_at=datetime.utcnow(),
                    last_activity_at=datetime.utcnow(),
                    total_turns=0,
                    total_duration_seconds=0,
                )
                db.add(db_session)
                await db.flush()
                await db.commit()
                break

        async for db in get_db_session():
            state = await _load_or_init_state(db, session_id, customer_persona.initial_mood)
            break

        budget_manager = BudgetManager()
        model_gateway = ModelGateway(budget_manager=budget_manager)
        coordinator = get_production_coordinator(
            model_gateway=model_gateway,
            budget_manager=budget_manager,
            persona=customer_persona,
        )
        coordinator.initialize_session(session_id, user_id, state)
        manager.set_orchestrator(session_id, coordinator)
        orchestrator = manager.get_orchestrator(session_id) or coordinator

        await manager.send_json(
            session_id,
            {
                "type": "init",
                "session_id": session_id,
                "stage": state.current_stage.value,
                "user_id": user_id,
                "persona": {"name": customer_persona.name, "occupation": customer_persona.occupation},
                "scenario": {"name": scenario_config.name, "product_category": scenario_config.product_category},
                "course": {"name": course.name},
            },
        )

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await manager.send_json(session_id, {"type": "pong"})
                continue
            if msg_type == "ack":
                await manager.ack_chunk(session_id, data.get("sequence", -1))
                continue
            if msg_type == "feedback":
                feedback_type = (data.get("feedback_type") or data.get("type_name") or "").lower()
                if not feedback_type and data.get("decision_id"):
                    feedback_type = "bandit"
                if feedback_type == "bandit":
                    decision_id = data.get("decision_id")
                    reward_raw = data.get("reward", data.get("score", 0.0))
                    reward = float(reward_raw) if reward_raw is not None else 0.0
                    signals = data.get("signals") or {}
                    ok = await orchestrator.record_bandit_feedback(decision_id, reward, signals)
                    await manager.send_json(session_id, {"type": "feedback_ack", "ok": ok})
                else:
                    await manager.send_json(session_id, {"type": "feedback_ack", "ok": False})
                continue
            if msg_type == "feedback_test":
                decision_id = data.get("decision_id") or getattr(orchestrator, "last_bandit_decision_id", None)
                reward = float(data.get("reward", 0.1))
                ok = await orchestrator.record_bandit_feedback(
                    decision_id,
                    reward,
                    {"test_signal": 1.0},
                )
                await manager.send_json(
                    session_id,
                    {"type": "feedback_test_ack", "ok": ok, "decision_id": decision_id, "reward": reward},
                )
                continue

            if msg_type in ["message", "text"]:
                content = (data.get("content") or "").strip()
                client_turn_id = data.get("turn_id") or data.get("client_turn_id")
                if not content:
                    await manager.send_json(session_id, {"type": "error", "message": "Empty message"})
                    continue
                await _process_user_message(
                    session_id,
                    user_id,
                    content,
                    orchestrator,
                    tenant_id=getattr(current_user, "tenant_id", None),
                    client_turn_id=client_turn_id,
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", session_id)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc, exc_info=True)
        try:
            message = str(exc) if settings.DEBUG else "Internal server error"
            await manager.send_json(session_id, {"type": "error", "message": message})
        except Exception:
            pass
    finally:
        if session_id:
            try:
                async for db in get_db_session():
                    result = await db.execute(select(Session).where(Session.id == session_id))
                    db_session = result.scalar_one_or_none()
                    if db_session:
                        db_session.status = "completed"
                        db_session.last_activity_at = datetime.utcnow()
                        await db.commit()
                    break
            except Exception:
                pass
        if session_id:
            await manager.disconnect(session_id, user_id)


def _stable_turn_id(
    session_id: str,
    user_id: str,
    content: str,
    turn_number: int,
    client_turn_id: Optional[str] = None,
) -> str:
    if client_turn_id:
        return str(client_turn_id)
    raw = f"{session_id}:{user_id}:{turn_number}:{content}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _is_recent(created_at: Optional[datetime], window_seconds: int) -> bool:
    if not created_at:
        return False
    return datetime.utcnow() - created_at < timedelta(seconds=window_seconds)


def _build_ws_error_payload(exc: Exception, settings) -> dict:
    if isinstance(exc, AuditBlockedError):
        payload = {"type": "error", "category": "user_error", "message": "Output blocked by policy"}
    elif isinstance(exc, (CognitiveTimeoutError, TimeoutError)):
        payload = {"type": "error", "category": "system_error", "message": "Request timed out"}
    elif isinstance(exc, CognitiveError):
        payload = {"type": "error", "category": "system_error", "message": "Internal server error"}
    else:
        payload = {"type": "error", "category": "system_error", "message": "Internal server error"}
    if settings.DEBUG:
        payload["detail"] = repr(exc)
    return payload


async def _send_committed_turn(session_id: str, turn_id: str, db: AsyncSession) -> bool:
    npc_result = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.turn_id == turn_id,
            Message.role == "npc",
            Message.status == "committed",
        )
        .order_by(Message.turn_number.desc())
        .limit(1)
    )
    npc_msg = npc_result.scalar_one_or_none()
    if not npc_msg:
        return False
    user_result = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.turn_id == turn_id,
            Message.role == "user",
            Message.status == "committed",
        )
        .order_by(Message.turn_number.desc())
        .limit(1)
    )
    user_msg = user_result.scalar_one_or_none()
    await manager.send_json(
        session_id,
        {
            "type": "turn_result",
            "turn": npc_msg.turn_number,
            "user_message": user_msg.content if user_msg else "",
            "npc_response": npc_msg.content,
            "npc_mood": (npc_msg.npc_result or {}).get("mood_after", 0.5),
            "stage": npc_msg.stage,
            "ttfs_ms": 0,
            "turn_id": turn_id,
        },
    )
    return True


async def _process_user_message(
    session_id: str,
    user_id: str,
    content: str,
    orchestrator: ProductionCoordinator,
    tenant_id: Optional[str] = None,
    client_turn_id: Optional[str] = None,
) -> None:
    db = None
    async for db_tmp in get_db_session():
        db = db_tmp
        break
    if not db:
        return

    session_result = await db.execute(select(Session).where(Session.id == session_id))
    session_row = session_result.scalar_one_or_none()
    if not session_row:
        await manager.send_json(session_id, {"type": "error", "message": "Session not found"})
        return

    state_result = await db.execute(select(SessionState).where(SessionState.session_id == session_id))
    session_state = state_result.scalar_one_or_none()
    history_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id, Message.status == "committed")
        .order_by(Message.turn_number.desc())
        .limit(5)
    )
    history_msgs = list(reversed(history_result.scalars().all()))
    session_ctx = {
        "history": [{"role": m.role, "content": m.content} for m in history_msgs],
        "persona": None,
        "stage": session_state.current_stage if session_state else "training",
    }
    current_stage = session_ctx.get("stage", "training")
    previous_stage = current_stage
    turn_number = session_row.total_turns + 1
    turn_id = _stable_turn_id(session_id, user_id, content, turn_number, client_turn_id=client_turn_id)

    existing_user_result = await db.execute(
        select(Message).where(
            Message.session_id == session_id,
            Message.turn_id == turn_id,
            Message.role == "user",
        )
    )
    existing_user = existing_user_result.scalar_one_or_none()
    if existing_user:
        if existing_user.status == "committed":
            await _send_committed_turn(session_id, turn_id, db)
            return
        if not _is_recent(existing_user.created_at, 30):
            if existing_user.content != content:
                await manager.send_json(
                    session_id,
                    {"type": "error", "category": "system_error", "message": "Turn conflict"},
                )
                return
        else:
            return
    else:
        recent_user_result = await db.execute(
            select(Message)
            .where(
                Message.session_id == session_id,
                Message.role == "user",
                Message.status == "committed",
            )
            .order_by(Message.turn_number.desc())
            .limit(1)
        )
        recent_user = recent_user_result.scalar_one_or_none()
        if recent_user and recent_user.content == content and _is_recent(recent_user.created_at, 30):
            await _send_committed_turn(session_id, recent_user.turn_id or "", db)
            return

    if manager.is_duplicate_turn(session_id, turn_id):
        await _send_committed_turn(session_id, turn_id, db)
        return
    manager.mark_turn_seen(session_id, turn_id)

    if not existing_user:
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=turn_number,
            role="user",
            content=content,
            stage=current_stage,
            turn_id=turn_id,
            status="pending",
        )
        db.add(user_msg)
        await db.commit()
    else:
        user_msg = existing_user

    def _emit(event: dict) -> None:
        asyncio.create_task(manager.send_json(session_id, {"type": "round_event", **event}))

    start_time = time.time()
    try:
        result = await orchestrator.execute_turn(
            turn_number=turn_number,
            user_message=content,
            enable_async_coach=True,
        )
        reply = result.npc_response
        npc_mood = result.npc_mood
        current_stage = result.stage or current_stage
        ttfs_ms = result.ttft_ms
        bandit_decision = result.bandit_decision if hasattr(result, "bandit_decision") else None
        metadata = result.metadata if hasattr(result, "metadata") else None
    except Exception as e:
        manager.clear_turn_seen(session_id, turn_id)
        if isinstance(e, AuditBlockedError):
            performance_metrics_collector.record_audit_block()
        else:
            performance_metrics_collector.record_error()
        settings = get_settings()
        await manager.send_json(session_id, _build_ws_error_payload(e, settings))
        return

    latency_ms = (time.time() - start_time) * 1000
    performance_metrics_collector.record_turn(latency_ms=latency_ms)

    npc_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        turn_number=turn_number,
        role="npc",
        content=reply,
        stage=current_stage,
        npc_result={"mood_after": npc_mood if 'npc_mood' in locals() else 0.5},
        turn_id=turn_id,
        status="committed",
    )
    db.add(npc_msg)

    user_msg.status = "committed"
    session_row.total_turns = turn_number
    session_row.last_activity_at = datetime.utcnow()

    if session_state:
        session_state.current_stage = current_stage
        session_state.turn_count = turn_number
        session_state.context_snapshot = {
            "turn": turn_number,
            "stage": current_stage,
            "history_tail": session_ctx["history"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    await db.commit()

    try:
        from app.context_manager import context_manager

        await context_manager.process_turn(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id or "",
            turn_id=turn_number,
            current_stage=str(current_stage),
            previous_stage=str(previous_stage),
            user_input=content,
            npc_response=reply,
            history_window=session_ctx.get("history", []),
        )
    except Exception as exc:
        logger.warning("Context manager update failed: %s", exc)

    await manager.send_json(
        session_id,
        {
            "type": "turn_result",
            "turn": turn_number,
            "user_message": content,
            "npc_response": reply,
            "npc_mood": 0.5,
            "stage": current_stage,
            "ttfs_ms": ttfs_ms if 'ttfs_ms' in locals() else 0,
            "turn_id": turn_id,
            "bandit_decision_id": (bandit_decision or {}).get("decision_id") if 'bandit_decision' in locals() else None,
            "metadata": metadata or {},
        },
    )


async def _load_course(db: AsyncSession, course_id: str, session_id: str) -> Optional[Course]:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        await manager.send_json(session_id, {"type": "error", "message": f"Course not found: {course_id}"})
    return course


async def _load_scenario(db: AsyncSession, scenario_id: str, session_id: str) -> Optional[ScenarioConfig]:
    result = await db.execute(select(ScenarioConfig).where(ScenarioConfig.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        await manager.send_json(session_id, {"type": "error", "message": f"Scenario not found: {scenario_id}"})
    return scenario


async def _load_persona(db: AsyncSession, persona_id: str, session_id: str) -> Optional[CustomerPersona]:
    result = await db.execute(select(CustomerPersona).where(CustomerPersona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        await manager.send_json(session_id, {"type": "error", "message": f"Persona not found: {persona_id}"})
    return persona


async def _load_or_init_state(db: AsyncSession, session_id: str, initial_mood: float) -> FSMState:
    state_result = await db.execute(select(SessionState).where(SessionState.session_id == session_id))
    session_state = state_result.scalar_one_or_none()
    if session_state:
        return FSMState(
            current_stage=SalesStage(session_state.current_stage),
            turn_count=session_state.turn_count,
            npc_mood=session_state.npc_mood,
        )

    fsm_state = FSMState(current_stage=SalesStage.OPENING, turn_count=0, npc_mood=initial_mood)
    session_state = SessionState(
        id=str(uuid.uuid4()),
        session_id=session_id,
        current_stage=fsm_state.current_stage.value,
        stage_history=[fsm_state.current_stage.value],
        slot_values={},
        stage_coverages={},
        goal_achieved={},
        npc_mood=initial_mood,
        turn_count=0,
        context_snapshot={
            "turn": 0,
            "stage": fsm_state.current_stage.value,
            "npc_mood": initial_mood,
            "history_tail": [],
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
    db.add(session_state)
    await db.commit()
    return fsm_state


def _split_chunks(text: str, chunk_size: int = 120) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

