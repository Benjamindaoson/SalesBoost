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
from app.core.config import get_settings
from app.services.orchestrator import SessionOrchestrator
from app.services.v3_orchestrator import V3Orchestrator
from app.models.config_models import ScenarioConfig, CustomerPersona, Course
from app.models.runtime_models import Session, Message, SessionState
from app.schemas.fsm import SalesStage
from typing import Union

logger = logging.getLogger(__name__)
router = APIRouter()


from app.core.redis import get_redis_client # 假设有这个工具函数
import asyncio
import json

class ConnectionInfo:
    """连接信息 (支持心跳)"""
    def __init__(self, websocket: WebSocket, session_id: str, db: AsyncSession):
        self.websocket = websocket
        self.session_id = session_id
        self.db = db
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow().timestamp()

class ConnectionManager:
    """WebSocket 连接管理器 (支持 Redis 广播 & 僵尸清理)"""
    
    def __init__(self):
        self.active_connections: dict[str, ConnectionInfo] = {}
        self.orchestrators: dict[str, SessionOrchestrator] = {}
        self.redis = None # Lazy init
        self.instance_id = str(uuid.uuid4())
        self.cleanup_task = None
    
    async def _get_redis(self):
        if not self.redis:
            self.redis = await get_redis_client()
        return self.redis

    async def connect(self, websocket: WebSocket, session_id: str, db: AsyncSession):
        await websocket.accept()
        # 封装为 ConnectionInfo
        info = ConnectionInfo(websocket, session_id, db)
        self.active_connections[session_id] = info
        logger.info(f"WebSocket connected: {session_id} (Instance: {self.instance_id})")
        
        # 启动清理任务（如果是第一个连接）
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self.start_cleanup_loop())
        
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].websocket.close()
            except:
                pass
            del self.active_connections[session_id]
            
        # 清理 Orchestrator 资源 (Agent Lifecycle P1)
        if session_id in self.orchestrators:
            orch = self.orchestrators[session_id]
            orch.dispose()
            del self.orchestrators[session_id]
            
        # 注意：DB session 由 caller 管理还是 manager 管理？
        # 目前是 connect 传入的，似乎是 caller (websocket_endpoint) 通过 yield 获取的。
        # 如果 websocket_endpoint 退出，db 会自动 close (FastAPI deps).
        # 但如果是 cleanup_zombies 触发的 disconnect，我们需要手动 close 吗？
        # ConnectionInfo 存了 db。
        # 这里的 db 是 AsyncSession。
        # 如果 websocket_endpoint 还在 await receive_json，我们这里 close socket，
        # websocket_endpoint 会抛出 WebSocketDisconnect，然后 finally 块会处理 db cleanup。
        # 所以这里不需要手动 close db。
        
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_json(self, session_id: str, data: dict):
        # 心跳消息不记录日志
        if data.get("type") not in ["pong", "ping"]:
            logger.debug(f"WS Send to {session_id}: {data.get('type')}")
        
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].websocket.send_json(data)
            except Exception as e:
                logger.error(f"WS Send failed: {e}")
                await self.disconnect(session_id)

    async def update_heartbeat(self, session_id: str):
        """更新心跳时间"""
        if session_id in self.active_connections:
            self.active_connections[session_id].last_heartbeat = datetime.utcnow().timestamp()

    async def start_cleanup_loop(self):
        """后台任务：清理僵尸连接"""
        logger.info("Starting zombie connection cleanup loop")
        while True:
            try:
                await asyncio.sleep(60) # 每分钟检查一次
                now = datetime.utcnow().timestamp()
                # 复制 keys 防止遍历时修改
                for session_id in list(self.active_connections.keys()):
                    info = self.active_connections[session_id]
                    # 5分钟无心跳视为僵尸 (客户端应每30s ping一次)
                    if now - info.last_heartbeat > 300:
                        logger.warning(f"Closing zombie connection: {session_id}")
                        await self.disconnect(session_id)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60) # 出错后等待

    def set_orchestrator(self, session_id: str, orchestrator: Union[SessionOrchestrator, V3Orchestrator]):
        self.orchestrators[session_id] = orchestrator
    
    def get_orchestrator(self, session_id: str) -> Optional[Union[SessionOrchestrator, V3Orchestrator]]:
        return self.orchestrators.get(session_id)
    
    def get_db(self, session_id: str) -> Optional[AsyncSession]:
        if session_id in self.active_connections:
            return self.active_connections[session_id].db
        return None


manager = ConnectionManager()


@router.websocket("/ws/train")
async def websocket_training(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    course_id: Optional[str] = Query(None),
    scenario_id: Optional[str] = Query(None),
    persona_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """
    WebSocket 训练端点 - 真实数据库集成
    
    连接参数（两种方式）：
    方式1：通过 session_id 连接已存在的会话
    - session_id: 会话 ID
    
    方式2：创建新会话
    - course_id: 课程 ID
    - scenario_id: 场景 ID
    - persona_id: 人设 ID
    - user_id: 用户 ID
    """
    db = None
    
    try:
        # 获取数据库会话
        async for db_session in get_db_session():
            db = db_session
            break
        
        if not db:
            await websocket.close(code=1011, reason="Database connection failed")
            return
        
        # 如果提供了 session_id，从数据库加载会话
        if session_id:
            session_result = await db.execute(
                select(Session).where(Session.id == session_id)
            )
            db_session = session_result.scalar_one_or_none()
            
            if not db_session:
                await websocket.close(code=404, reason=f"Session not found: {session_id}")
                return
            
            # 使用已存在的会话信息
            course_id = db_session.course_id
            scenario_id = db_session.scenario_id
            persona_id = db_session.persona_id
            user_id = db_session.user_id
        else:
            # 创建新会话
            if not all([course_id, scenario_id, persona_id, user_id]):
                await websocket.close(code=400, reason="Missing required parameters: course_id, scenario_id, persona_id, user_id")
                return
            
            session_id = str(uuid.uuid4())
            db_session = None
        
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
        
        # 如果 db_session 不存在（新会话），创建 Session 并落盘
        if not db_session:
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
        
        # 根据配置选择 V2 或 V3 Orchestrator
        from app.core.config import get_settings
        settings = get_settings()
        
        if settings.AGENTIC_V3_ENABLED:
            # V3 架构
            logger.info(f"Using V3 Orchestrator for session {session_id}")
            from app.services.v3_orchestrator import V3Orchestrator
            from app.services.model_gateway import ModelGateway, BudgetManager
            from app.agents.v3.session_director_v3 import SessionDirectorV3
            
            model_gateway = ModelGateway()
            budget_manager = BudgetManager()
            session_director = SessionDirectorV3(model_gateway, budget_manager)
            
            v3_orchestrator = V3Orchestrator(
                model_gateway=model_gateway,
                budget_manager=budget_manager,
                session_director=session_director,
                persona=customer_persona,
            )
            
            # 初始化 FSM State
            fsm_engine = FSMEngine()
            fsm_state = fsm_engine.create_initial_state()
            
            await v3_orchestrator.initialize_session(session_id, user_id, fsm_state)
            manager.set_orchestrator(session_id, v3_orchestrator)
            orchestrator = v3_orchestrator
        else:
            # V2 架构（原有逻辑）
            logger.info(f"Using V2 Orchestrator for session {session_id}")
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
        
        # 创建或更新 SessionState 并落盘
        try:
            state_result = await db.execute(
                select(SessionState).where(SessionState.session_id == session_id)
            )
            session_state = state_result.scalar_one_or_none()
            
            if not session_state:
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
            else:
                # 更新现有状态
                session_state.current_stage = fsm_state.current_stage.value
                if fsm_state.current_stage.value not in session_state.stage_history:
                    session_state.stage_history.append(fsm_state.current_stage.value)
            
            await db.commit()
            logger.info(f"SessionState created/updated in DB")
        except Exception as e:
            logger.error(f"Failed to create/update session state: {e}")
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
                await manager.update_heartbeat(session_id)
                await manager.send_json(session_id, {"type": "pong"})
                continue
            
            # 支持两种消息类型：message 和 text
            if msg_type in ["message", "text"]:
                await manager.update_heartbeat(session_id)
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
        
        await manager.disconnect(session_id)


async def _process_user_message(
    session_id: str,
    user_id: str,
    content: str,
    orchestrator: Union[SessionOrchestrator, V3Orchestrator],
    db_session: Session,
):
    """
    处理用户消息 - 异步非阻塞模式
    1. 立即生成 NPC 回复并发送 (process_interaction)
    2. 后台执行复杂分析与落盘 (process_analysis)
    """
    db = manager.get_db(session_id)
    if not db:
        logger.error("No DB session found")
        return
    
    settings = get_settings()
    
    try:
        # V3 架构路径
        if settings.AGENTIC_V3_ENABLED and isinstance(orchestrator, V3Orchestrator):
            # V3: 使用双流架构
            current_turn = orchestrator.fsm_state.turn_count + 1 if orchestrator.fsm_state else 1
            
            v3_result = await orchestrator.process_turn(
                turn_number=current_turn,
                user_message=content,
                db=db,
            )
            
            # 指标埋点：记录路由和降级信息
            metrics = orchestrator.get_metrics()
            
            # 立即发送 Fast Path 结果（NPC 回复）
            await manager.send_json(session_id, {
                "type": "turn_result_partial",
                "turn": v3_result.turn_number,
                "user_message": content,
                "npc_response": v3_result.fast_path_result.npc_reply.response,
                "npc_mood": v3_result.fast_path_result.npc_reply.mood_after,
                "processing_time_ms": v3_result.fast_path_result.ttfs_ms,
                "stage": orchestrator.fsm_state.current_stage.value if orchestrator.fsm_state else "OPENING",
                "ttfs_ms": v3_result.fast_path_result.ttfs_ms,  # V3 指标
                "metrics": {
                    "fast_path_ttfs_ms": v3_result.fast_path_result.ttfs_ms,
                    "provider_hits": metrics.get("provider_hits", {}),
                },
            })
            
            # Slow Path 异步执行（已在 process_turn 中创建 task）
            # 注意：Slow Path 结果会异步推送，这里不等待
            # Slow Path 完成后会通过 WebSocket 推送 turn_analysis 消息
            
        else:
            # V2 架构路径（原有逻辑）
            turn_result_partial = await orchestrator.process_interaction(
                user_message=content,
            )
            
            # 立即发送 NPC 回复给用户
            await manager.send_json(session_id, {
                "type": "turn_result_partial",
                "turn": turn_result_partial.turn_number,
                "user_message": turn_result_partial.user_message,
                "npc_response": turn_result_partial.npc_result.response,
                "npc_mood": turn_result_partial.npc_result.mood_after,
                "processing_time_ms": turn_result_partial.processing_time_ms,
                "stage": turn_result_partial.fsm_state_snapshot.current_stage.value,
            })
            
            # [Step 2] 后台分析：Coach, Eval, DB
            asyncio.create_task(_run_analysis_and_save(
                session_id, user_id, content,
                orchestrator, db_session, db,
                turn_result_partial
            ))
        
    except Exception as e:
        logger.error(f"Process interaction error: {e}", exc_info=True)
        await manager.send_json(session_id, {
            "type": "error",
            "message": f"处理消息时出错: {str(e)}",
        })


async def _send_slow_path_result(
    session_id: str,
    v3_result: "V3TurnResult",
    orchestrator: V3Orchestrator,
):
    """等待 Slow Path 完成并发送结果"""
    # 注意：这里需要等待 Slow Path 完成
    # 实际实现中，Slow Path 结果应该通过回调或事件机制发送
    # 这里先 stub，实际需要重构 Slow Path 的返回机制
    await asyncio.sleep(5)  # 等待 Slow Path 完成
    
    # 获取 Slow Path 结果（需要从 orchestrator 获取）
    # TODO: 实现 Slow Path 结果获取机制
    logger.info(f"Slow Path result should be sent for turn {v3_result.turn_number}")

async def _run_analysis_and_save(
    session_id: str,
    user_id: str,
    content: str,
    orchestrator: SessionOrchestrator,
    db_session: Session,
    db: AsyncSession,
    turn_result: "OrchestratorTurnResult"
):
    """后台任务：执行分析、落盘、发送剩余结果"""
    try:
        # 执行分析 (Coach, Eval, Strategy, Adoption, State Update)
        # 注意：process_analysis 会更新 FSM State，这可能会与下一轮 Interaction 竞争
        # 但由于 Interaction 只读 State，且 Update 在 Analysis 尾部，风险可控
        # 真正的风险是：用户在 Analysis 完成前发送了下一条消息，导致下一条消息基于旧 State 处理
        # 在 Sales 场景下，Stage 变迁通常不频繁，且用户打字需要时间，故可接受
        
        full_result = await orchestrator.process_analysis(turn_result, db)
        
        # 保存消息记录 (Message Table)
        # 必须在 Analysis 阶段做，因为需要 DB 事务
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=full_result.turn_number,
            role="user",
            content=content,
            stage=full_result.fsm_state_snapshot.current_stage.value,
        )
        db.add(user_msg)
        
        npc_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            turn_number=full_result.turn_number,
            role="npc",
            content=full_result.npc_result.response,
            stage=full_result.fsm_state_snapshot.current_stage.value,
            npc_result={"mood_after": full_result.npc_result.mood_after},
        )
        db.add(npc_msg)
        
        # 更新 Session 统计
        db_session.total_turns = full_result.turn_number
        db_session.last_activity_at = datetime.utcnow()
        
        # 更新 SessionState 表
        state_result = await db.execute(
            select(SessionState).where(SessionState.session_id == session_id)
        )
        session_state = state_result.scalar_one_or_none()
        if session_state:
            session_state.current_stage = full_result.fsm_state_snapshot.current_stage.value
            session_state.npc_mood = full_result.npc_result.mood_after
            session_state.turn_count = full_result.turn_number
        
        # 提交所有更改
        await db.commit()
        
        # MVP: 生成快速建议 (可以并行，这里简单串行)
        from app.services.quick_suggest_service import QuickSuggestService
        quick_suggest_service = QuickSuggestService()
        quick_suggest = None
        try:
            quick_suggest = await quick_suggest_service.generate_suggest(
                session_id=session_id,
                last_user_msg=content,
                conversation_history=orchestrator.conversation_history,
                fsm_state=full_result.fsm_state_snapshot,
            )
        except Exception as e:
            logger.error(f"Failed to generate quick suggest: {e}")

        # 发送完整的 Analysis 结果 (前端侧边栏更新)
        analysis_msg = {
            "type": "turn_analysis", # 前端根据此类型更新侧边栏
            "turn": full_result.turn_number,
            "coach_suggestion": full_result.coach_result.suggestion,
            "coach_example": full_result.coach_result.example_utterance,
            "scores": full_result.evaluator_result.dimension_scores,
            "overall_score": full_result.evaluator_result.overall_score,
            "goal_advanced": full_result.evaluator_result.goal_advanced,
            "compliance_passed": full_result.compliance_result.is_compliant,
            "compliance_risks": [
                {"type": r.risk_type, "reason": r.risk_reason}
                for r in full_result.compliance_result.risk_flags
            ] if full_result.compliance_result.risk_flags else [],
            "compliance_safe_rewrite": full_result.compliance_result.safe_rewrite,
        }
        
        if quick_suggest:
            analysis_msg["quick_suggest"] = {
                "intent_label": quick_suggest.intent_label.value,
                "suggested_reply": quick_suggest.suggested_reply,
                "alt_replies": quick_suggest.alt_replies,
                "confidence": quick_suggest.confidence,
                "evidence": quick_suggest.evidence,
            }
            
        if full_result.strategy_analysis:
            analysis_msg["strategy_analysis"] = full_result.strategy_analysis
        if full_result.strategy_guidance:
            analysis_msg["strategy_guidance"] = full_result.strategy_guidance
        if full_result.adoption_analysis:
            analysis_msg["adoption_analysis"] = full_result.adoption_analysis
            
        await manager.send_json(session_id, analysis_msg)
        
        # 检查阶段变化
        if full_result.transition_decision.should_transition:
            await manager.send_json(session_id, {
                "type": "stage_change",
                "from": full_result.transition_decision.from_stage.value,
                "to": full_result.transition_decision.to_stage.value if full_result.transition_decision.to_stage else None,
                "reason": full_result.transition_decision.reason,
            })
            
        # 检查会话完成 (复盘)
        if orchestrator.is_session_completed():
            # ... (复盘逻辑保持不变，略微简化)
            # 由于代码量限制，这里直接复用原有逻辑，但需注意在 task 中执行
            db_session.status = "completed"
            db_session.completed_at = datetime.utcnow()
            
            from app.services.micro_feedback_service import MicroFeedbackService
            feedback_service = MicroFeedbackService()
            try:
                feedback_response = await feedback_service.generate_feedback(session_id, db)
                from app.models.feedback_models import SessionFeedback
                feedback_record = SessionFeedback(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    feedback_items=[item.model_dump() for item in feedback_response.feedback_items],
                    total_turns=feedback_response.total_turns,
                    generated_at=datetime.utcnow(),
                )
                db.add(feedback_record)
            except:
                feedback_response = None
            
            completion_result = await orchestrator.complete_session(db)
            await db.commit()
            
            complete_msg = {
                "type": "session_complete",
                "final_stage": full_result.fsm_state_snapshot.current_stage.value,
                "total_turns": full_result.turn_number,
                "message": "恭喜完成本次训练！",
            }
            if completion_result:
                complete_msg.update(completion_result)
            if feedback_response:
                complete_msg["micro_feedback"] = {
                    "feedback_items": [item.model_dump() for item in feedback_response.feedback_items],
                    "total_turns": feedback_response.total_turns,
                }
            await manager.send_json(session_id, complete_msg)

    except Exception as e:
        logger.error(f"Background analysis error: {e}", exc_info=True)
        # 回滚事务
        try:
            await db.rollback()
        except:
            pass
        # 通知用户后台错误（可选）
        await manager.send_json(session_id, {
            "type": "error",
            "message": "后台分析服务暂时不可用，但您可以继续对话",
        })
