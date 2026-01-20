"""
WebSocket Endpoint - 真实数据库集成版本
实时训练会话，所有数据从数据库加载并落盘
"""
import logging
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db_session
from app.services.orchestrator import SessionOrchestrator
from app.models.config_models import ScenarioConfig, CustomerPersona, Course
from app.models.runtime_models import Session, Message, SessionState
from app.schemas.fsm import SalesStage

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.orchestrators: dict[str, SessionOrchestrator] = {}
        self.db_sessions: dict[str, AsyncSession] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, db: AsyncSession):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.db_sessions[session_id] = db
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.orchestrators:
            del self.orchestrators[session_id]
        if session_id in self.db_sessions:
            del self.db_sessions[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)
    
    def set_orchestrator(self, session_id: str, orchestrator: SessionOrchestrator):
        self.orchestrators[session_id] = orchestrator
    
    def get_orchestrator(self, session_id: str) -> Optional[SessionOrchestrator]:
        return self.orchestrators.get(session_id)
    
    def get_db(self, session_id: str) -> Optional[AsyncSession]:
        return self.db_sessions.get(session_id)


manager = ConnectionManager()


@router.websocket("/ws/train")
async def websocket_training(
    websocket: WebSocket,
    course_id: str = Query(...),
    scenario_id: str = Query(...),
    persona_id: str = Query(...),
    user_id: str = Query(...),
):
    """
    WebSocket 训练端点 - 真实数据库集成
    
    连接参数：
    - course_id: 课程 ID
    - scenario_id: 场景 ID
    - persona_id: 人设 ID
    - user_id: 用户 ID
    """
    session_id = str(uuid.uuid4())
    db = None
    
    try:
        # 获取数据库会话
        async for db_session in get_db_session():
            db = db_session
            break
        
        if not db:
            await websocket.close(code=1011, reason="Database connection failed")
            return
        
        await manager.connect(websocket, session_id, db)
        
        # 从数据库加载真实配置
        try:
            # 加载课程
            course_result = await db.execute(
                select(Course).where(Course.id == course_id)
            )
            course = course_result.scalar_one_or_none()
            if not course:
                await manager.send_json(session_id, {
                    "type": "error",
                    "message": f"Course not found: {course_id}"
                })
                return
            
            # 加载场景配置
            scenario_result = await db.execute(
                select(ScenarioConfig).where(ScenarioConfig.id == scenario_id)
            )
            scenario_config = scenario_result.scalar_one_or_none()
            if not scenario_config:
                await manager.send_json(session_id, {
                    "type": "error",
                    "message": f"Scenario not found: {scenario_id}"
                })
                return
            
            # 加载客户人设
            persona_result = await db.execute(
                select(CustomerPersona).where(CustomerPersona.id == persona_id)
            )
            customer_persona = persona_result.scalar_one_or_none()
            if not customer_persona:
                await manager.send_json(session_id, {
                    "type": "error",
                    "message": f"Persona not found: {persona_id}"
                })
                return
            
            logger.info(f"Loaded: Course={course.name}, Scenario={scenario_config.name}, Persona={customer_persona.name}")
            
        except Exception as e:
            logger.error(f"Failed to load config from DB: {e}")
            await manager.send_json(session_id, {
                "type": "error",
                "message": f"Failed to load configuration: {str(e)}"
            })
            return
        
        # 创建真实 Session 并落盘
        try:
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
            logger.info(f"Session created in DB: {session_id}")
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await manager.send_json(session_id, {
                "type": "error",
                "message": f"Failed to create session: {str(e)}"
            })
            return
        
        # 创建编排器
        orchestrator = SessionOrchestrator(
            scenario_config=scenario_config,
            customer_persona=customer_persona,
        )
        
        # 初始化会话
        fsm_state = await orchestrator.initialize_session(
            session_id=session_id,
            user_id=user_id,
        )
        manager.set_orchestrator(session_id, orchestrator)
        
        # 创建 SessionState 并落盘
        try:
            session_state = SessionState(
                id=str(uuid.uuid4()),
                session_id=session_id,
                current_stage=fsm_state.current_stage.value,
                stage_history=[fsm_state.current_stage.value],
                slot_values={},
                stage_coverages={},
                goal_achieved={},
                npc_mood=customer_persona.initial_mood,
                turn_count=0,
            )
            db.add(session_state)
            await db.commit()
            logger.info(f"SessionState created in DB")
        except Exception as e:
            logger.error(f"Failed to create session state: {e}")
            await db.rollback()
        
        # 发送初始化消息
        await manager.send_json(session_id, {
            "type": "init",
            "session_id": session_id,
            "stage": fsm_state.current_stage.value,
            "user_id": user_id,
            "persona": {
                "name": customer_persona.name,
                "occupation": customer_persona.occupation,
            },
            "scenario": {
                "name": scenario_config.name,
                "product_category": scenario_config.product_category,
            },
            "course": {
                "name": course.name,
            }
        })
        
        # 消息循环
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await manager.send_json(session_id, {"type": "pong"})
                continue
            
            if msg_type == "message":
                content = data.get("content", "").strip()
                if not content:
                    await manager.send_json(session_id, {
                        "type": "error",
                        "message": "消息内容不能为空",
                    })
                    continue
                
                # 处理用户消息
                await _process_user_message(
                    session_id, user_id, content, 
                    orchestrator, db_session
                )
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await manager.send_json(session_id, {
                "type": "error",
                "message": str(e),
            })
        except:
            pass
    finally:
        # 更新 Session 状态
        if db and session_id:
            try:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                db_session = result.scalar_one_or_none()
                if db_session:
                    db_session.status = "completed"
                    db_session.last_activity_at = datetime.utcnow()
                    await db.commit()
            except:
                pass
        
        manager.disconnect(session_id)


async def _process_user_message(
    session_id: str,
    user_id: str,
    content: str,
    orchestrator: SessionOrchestrator,
    db_session: Session,
):
    """处理用户消息 - 真实数据库落盘"""
    db = manager.get_db(session_id)
    if not db:
        logger.error("No DB session found")
        return
    
    try:
        # 处理轮次
        result = await orchestrator.process_turn(
            user_message=content,
            session=db_session,
            db=db,
        )
        
        # 保存用户消息到数据库
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=result.turn_number,
            role="user",
            content=content,
            stage=result.fsm_state_snapshot.current_stage.value,
        )
        db.add(user_msg)
        
        # 保存 NPC 消息到数据库
        npc_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=result.turn_number,
            role="npc",
            content=result.npc_result.response,
            stage=result.fsm_state_snapshot.current_stage.value,
            npc_result={"mood_after": result.npc_result.mood_after},
        )
        db.add(npc_msg)
        
        # 更新 Session
        db_session.total_turns = result.turn_number
        db_session.last_activity_at = datetime.utcnow()
        
        # 更新 SessionState
        state_result = await db.execute(
            select(SessionState).where(SessionState.session_id == session_id)
        )
        session_state = state_result.scalar_one_or_none()
        if session_state:
            session_state.current_stage = result.fsm_state_snapshot.current_stage.value
            session_state.npc_mood = result.npc_result.mood_after
            session_state.turn_count = result.turn_number
        
        await db.commit()
        
        # 发送轮次结果
        turn_result_msg = {
            "type": "turn_result",
            "turn": result.turn_number,
            "user_message": result.user_message,
            "npc_response": result.npc_result.response,
            "npc_mood": result.npc_result.mood_after,
            "coach_suggestion": result.coach_result.suggestion,
            "coach_example": result.coach_result.example_utterance,
            "scores": result.evaluator_result.dimension_scores,
            "overall_score": result.evaluator_result.overall_score,
            "goal_advanced": result.evaluator_result.goal_advanced,
            "stage": result.fsm_state_snapshot.current_stage.value,
            "compliance_passed": result.compliance_result.is_compliant,
            "compliance_risks": [
                {"type": r.risk_type, "reason": r.risk_reason}
                for r in result.compliance_result.risk_flags
            ] if result.compliance_result.risk_flags else [],
            "processing_time_ms": result.processing_time_ms,
        }
        
        # 能力闭环数据 (已经是 dict 格式)
        if result.strategy_analysis:
            turn_result_msg["strategy_analysis"] = {
                "situation_type": result.strategy_analysis.get("situation_type"),
                "strategy_chosen": result.strategy_analysis.get("strategy_chosen"),
                "golden_strategy": result.strategy_analysis.get("golden_strategy"),
                "is_optimal": result.strategy_analysis.get("is_optimal"),
                "optimality_reason": result.strategy_analysis.get("optimality_reason"),
            }
        if result.strategy_guidance:
            turn_result_msg["strategy_guidance"] = {
                "golden_strategy": result.strategy_guidance.get("golden_strategy"),
                "transition_suggestion": result.strategy_guidance.get("transition_suggestion"),
                "example_utterance": result.strategy_guidance.get("example_utterance"),
            }
        if result.adoption_analysis:
            turn_result_msg["adoption_analysis"] = {
                "adoption_style": result.adoption_analysis.get("adoption_style"),
                "is_effective": result.adoption_analysis.get("is_effective"),
                "effectiveness_score": result.adoption_analysis.get("effectiveness_score"),
                "skill_delta": result.adoption_analysis.get("skill_delta"),
                "feedback_signal": result.adoption_analysis.get("feedback_signal"),
                "feedback_text": result.adoption_analysis.get("feedback_text"),
            }
            # Instant Feedback for Level Up (P1) - REMOVED (Handled by feedback_signal)
        
        await manager.send_json(session_id, turn_result_msg)
        
        # 检查阶段变化
        if result.transition_decision.should_transition:
            await manager.send_json(session_id, {
                "type": "stage_change",
                "from": result.transition_decision.from_stage.value,
                "to": result.transition_decision.to_stage.value if result.transition_decision.to_stage else None,
                "reason": result.transition_decision.reason,
            })
        
        # 检查会话完成
        if orchestrator.is_session_completed():
            db_session.status = "completed"
            db_session.completed_at = datetime.utcnow()
            
            # 触发 CurriculumPlanner
            completion_result = await orchestrator.complete_session(db)
            
            await db.commit()
            
            complete_msg = {
                "type": "session_complete",
                "final_stage": result.fsm_state_snapshot.current_stage.value,
                "total_turns": result.turn_number,
                "message": "恭喜完成本次训练！",
            }
            
            if completion_result:
                complete_msg["next_training_focus"] = completion_result.get("next_training_focus")
                complete_msg["overall_improvement"] = completion_result.get("overall_improvement")
            
            await manager.send_json(session_id, complete_msg)
    
    except Exception as e:
        logger.error(f"Process message error: {e}", exc_info=True)
        await db.rollback()
        await manager.send_json(session_id, {
            "type": "error",
            "message": f"处理消息时出错: {str(e)}",
        })
