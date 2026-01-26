"""
WebSocket endpoint for training sessions (V3).
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.coordination.v3_orchestrator import V3Orchestrator
from app.agents.v3.session_director_v3 import SessionDirectorV3
from app.core.database import get_db_session
from app.models.config_models import Course, CustomerPersona, ScenarioConfig
from app.models.runtime_models import Message, Session, SessionState
from app.schemas.fsm import FSMState, SalesStage
from app.services.model_gateway import ModelGateway
from app.services.model_gateway.budget import BudgetManager
from app.services.state_recovery import state_recovery_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.orchestrators: dict[str, V3Orchestrator] = {}
        self.pending_events: dict[str, dict[str, set[int]]] = {}
        self.recovery_enabled = True

    async def connect(
        self, websocket: WebSocket, session_id: str, user_id: str = "default_user"
    ) -> Optional[dict]:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.pending_events[session_id] = {}

        # 尝试恢复状态
        recovery_info = None
        if self.recovery_enabled and user_id:
            try:
                recovery_info = await state_recovery_service.recover_session_state(session_id, user_id)
                if recovery_info:
                    # 恢复编排器
                    self.orchestrators[session_id] = recovery_info["orchestrator"]
                    logger.info("Session state recovered: %s", session_id)
            except Exception as e:
                logger.error("State recovery failed for session %s: %s", session_id, e)

        logger.info("WebSocket connected: %s", session_id)
        return recovery_info

    async def disconnect(self, session_id: str, user_id: str = None) -> None:
        # 创建状态快照
        if self.recovery_enabled and user_id and session_id in self.orchestrators:
            try:
                await state_recovery_service.create_recovery_checkpoint(
                    session_id=session_id,
                    user_id=user_id,
                    agent_type="v3_orchestrator",
                    orchestrator=self.orchestrators[session_id],
                )
                logger.info("State snapshot created for session: %s", session_id)
            except Exception as e:
                logger.error("Failed to create state snapshot for session %s: %s", session_id, e)

        self.active_connections.pop(session_id, None)
        self.orchestrators.pop(session_id, None)
        self.pending_events.pop(session_id, None)
        logger.info("WebSocket disconnected: %s", session_id)

    async def send_json(self, session_id: str, data: dict) -> None:
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

    def set_orchestrator(self, session_id: str, orchestrator: V3Orchestrator) -> None:
        self.orchestrators[session_id] = orchestrator

    def get_orchestrator(self, session_id: str) -> Optional[V3Orchestrator]:
        return self.orchestrators.get(session_id)

    def get_db(self, session_id: str) -> Optional[AsyncSession]:
        return None

    def register_stream(self, session_id: str, event_id: str, total_chunks: int) -> None:
        self.pending_events.setdefault(session_id, {})[event_id] = set()
        logger.info("Stream registered: %s chunks=%s", event_id, total_chunks)

    def ack_stream(self, session_id: str, event_id: str, sequence: int) -> None:
        if session_id in self.pending_events and event_id in self.pending_events[session_id]:
            self.pending_events[session_id][event_id].add(sequence)


manager = ConnectionManager()


@router.get("/sessions/{user_id}/recoverable")
async def get_recoverable_sessions(user_id: str):
    """获取可恢复的会话列表"""
    try:
        sessions = await state_recovery_service.list_recoverable_sessions(user_id)
        return {"success": True, "data": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error("Failed to get recoverable sessions for user %s: %s", user_id, e)
        return {"success": False, "error": str(e)}


@router.post("/sessions/{session_id}/recover")
async def recover_session(session_id: str, user_id: str):
    """恢复特定会话"""
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
async def delete_session_snapshot(session_id: str, user_id: str):
    """删除会话快照"""
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
):
    try:
        await manager.connect(websocket, session_id or "", user_id or "default_user")

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
                course_id = db_session.course_id
                scenario_id = db_session.scenario_id
                persona_id = db_session.persona_id
                user_id = db_session.user_id
                break

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
                break

        async for db in get_db_session():
            state = await _load_or_init_state(db, session_id, customer_persona.initial_mood)
            break

        budget_manager = BudgetManager()
        model_gateway = ModelGateway(budget_manager=budget_manager)
        session_director = SessionDirectorV3(model_gateway, budget_manager)
        orchestrator = V3Orchestrator(
            model_gateway=model_gateway,
            budget_manager=budget_manager,
            session_director=session_director,
            persona=customer_persona,
        )
        orchestrator.initialize_session(session_id, user_id, state)
        manager.set_orchestrator(session_id, orchestrator)

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
                manager.ack_stream(session_id, data.get("event_id"), data.get("sequence", -1))
                continue

            if msg_type in ["message", "text"]:
                content = (data.get("content") or "").strip()
                if not content:
                    await manager.send_json(session_id, {"type": "error", "message": "Empty message"})
                    continue
                await _process_user_message(session_id, user_id, content, orchestrator, db_session)

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", session_id)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc, exc_info=True)
        try:
            await manager.send_json(session_id, {"type": "error", "message": str(exc)})
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
        manager.disconnect(session_id)


async def _process_user_message(
    session_id: str,
    user_id: str,
    content: str,
    orchestrator: V3Orchestrator,
    db_session: Session,
) -> None:
    db = None
    async for db_tmp in get_db_session():
        db = db_tmp
        break
    if not db:
        return

    event_id = str(uuid.uuid4())
    manager.register_stream(session_id, event_id, 0)
    await manager.send_json(session_id, {"type": "npc_stream_start", "event_id": event_id})

    npc_response_accumulator = []
    turn_result_data = None
    sequence = 0

    try:
        async for chunk in orchestrator.execute_turn_stream(
            turn_number=db_session.total_turns + 1,
            user_message=content,
            db=None,
        ):
            if chunk["type"] == "token":
                token = chunk["content"]
                npc_response_accumulator.append(token)
                await manager.send_json(
                    session_id,
                    {
                        "type": "npc_chunk",
                        "event_id": event_id,
                        "sequence": sequence,
                        "is_final": False,
                        "content": token,
                    },
                )
                sequence += 1
            elif chunk["type"] == "result":
                turn_result_data = chunk["data"]
            elif chunk["type"] == "error":
                await manager.send_json(session_id, {"type": "error", "message": chunk["message"]})
                return

    except Exception as e:
        logger.error(f"Stream execution failed: {e}")
        await manager.send_json(session_id, {"type": "error", "message": str(e)})
        return

    await manager.send_json(session_id, {"type": "npc_stream_end", "event_id": event_id})

    if not turn_result_data:
        logger.error("No result from orchestrator stream")
        return

    result = turn_result_data
    current_stage = orchestrator.fsm_state.current_stage.value

    user_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        turn_number=result.turn_number,
        role="user",
        content=content,
        stage=current_stage,
    )
    db.add(user_msg)
    npc_msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        turn_number=result.turn_number,
        role="npc",
        content=result.fast_path_result.npc_reply.response,
        stage=current_stage,
        npc_result={"mood_after": result.fast_path_result.npc_reply.mood_after},
    )
    db.add(npc_msg)

    db_session.total_turns = result.turn_number
    db_session.last_activity_at = datetime.utcnow()

    state_result = await db.execute(select(SessionState).where(SessionState.session_id == session_id))
    session_state = state_result.scalar_one_or_none()
    if session_state:
        session_state.current_stage = current_stage
        session_state.npc_mood = orchestrator.fsm_state.npc_mood
        session_state.turn_count = result.turn_number
        if current_stage not in session_state.stage_history:
            session_state.stage_history.append(current_stage)
        session_state.context_snapshot = {
            "turn": result.turn_number,
            "stage": current_stage,
            "npc_mood": orchestrator.fsm_state.npc_mood,
            "history_tail": orchestrator.conversation_history[-6:],
            "timestamp": datetime.utcnow().isoformat(),
        }

    await db.commit()

    await manager.send_json(
        session_id,
        {
            "type": "turn_result",
            "turn": result.turn_number,
            "user_message": content,
            "npc_response": result.fast_path_result.npc_reply.response,
            "npc_mood": result.fast_path_result.npc_reply.mood_after,
            "stage": orchestrator.fsm_state.current_stage.value,
            "ttfs_ms": result.fast_path_result.ttfs_ms,
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
