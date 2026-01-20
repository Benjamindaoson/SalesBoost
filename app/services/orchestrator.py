"""
Session Orchestrator - 会话编排器
唯一入口，驱动完整 Turn Loop
集成销冠能力复制系统：AdoptionTracker + StrategyAnalyzer

【能力闭环架构】
用户行为 → 策略选择(StrategyDecision) → Coach建议 → 是否被采纳(AdoptionRecord)
    → 能力是否提升(skill_delta) → 用户策略画像(UserStrategyProfile) → 下一步训练路径(CurriculumPlan)

【Turn Loop 能力相关动作（强制顺序）】
① 策略分析：每轮用户发言后，必须调用 StrategyAnalyzer.analyze_strategy 并写入 StrategyDecision
② 建议注册：Coach 产出建议后，注册 suggestion（baseline 只代表建议出现时的能力状态）
③ 采纳分析：每轮 Evaluator 完成后，必须调用 AdoptionTracker.analyze_adoption 检查前 1-2 轮建议是否被采纳
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.fsm import FSMState, SalesStage, TransitionDecision
from app.schemas.agent_outputs import (
    IntentGateOutput,
    NPCOutput,
    CoachOutput,
    EvaluatorOutput,
    RAGOutput,
    ComplianceOutput,
    OrchestratorTurnResult,
)
from app.schemas.strategy import StrategyAnalysis, StrategyGuidance, AdoptionAnalysis
from app.fsm.engine import FSMEngine
from app.agents.intent_gate import IntentGateAgent
from app.agents.npc_agent import NPCAgent
from app.agents.coach_agent import CoachAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.rag_agent import RAGAgent
from app.agents.compliance_agent import ComplianceAgent
from app.services.state_updater import StateUpdater
from app.services.adoption_tracker import AdoptionTracker
from app.services.strategy_analyzer import StrategyAnalyzer
from app.services.curriculum_planner import CurriculumPlanner
from app.models.config_models import ScenarioConfig, CustomerPersona
from app.models.runtime_models import Session, Message

logger = logging.getLogger(__name__)


class SessionOrchestrator:
    """
    会话编排器 - 唯一允许写能力因果账本的入口
    
    核心职责：
    - 驱动完整 Turn Loop
    - 协调各 Agent 执行
    - 【关键】管理能力闭环：策略分析 → 建议注册 → 采纳检测 → 落盘
    """
    
    def __init__(
        self,
        scenario_config: ScenarioConfig,
        customer_persona: CustomerPersona,
        fsm_engine: Optional[FSMEngine] = None,
    ):
        self.scenario_config = scenario_config
        self.customer_persona = customer_persona
        self.fsm_engine = fsm_engine or FSMEngine()
        
        # 初始化 Agents
        self.intent_gate = IntentGateAgent()
        self.npc_agent = NPCAgent(persona=customer_persona)
        self.coach_agent = CoachAgent()
        self.evaluator_agent = EvaluatorAgent()
        self.rag_agent = RAGAgent()
        self.compliance_agent = ComplianceAgent()
        
        # 状态更新器
        self.state_updater = StateUpdater(fsm_engine=self.fsm_engine)
        
        # 销冠能力复制系统 - 核心组件
        self.adoption_tracker = AdoptionTracker()
        self.strategy_analyzer = StrategyAnalyzer()
        self.curriculum_planner = CurriculumPlanner()
        
        # 会话状态
        self.fsm_state: Optional[FSMState] = None
        self.conversation_history: list[Dict[str, Any]] = []
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
    
    async def initialize_session(
        self,
        session_id: str,
        user_id: str,
    ) -> FSMState:
        """
        初始化会话
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID（必填，用于能力追踪）
        """
        self.session_id = session_id
        self.user_id = user_id
        self.fsm_state = self.fsm_engine.create_initial_state()
        self.conversation_history = []
        
        logger.info(f"Session initialized: {session_id}, user: {user_id}")
        return self.fsm_state

    async def process_turn(
        self,
        user_message: str,
        session: Session,
        db: AsyncSession,
    ) -> OrchestratorTurnResult:
        """
        处理单轮对话 - 包含完整能力闭环
        
        【能力闭环三步曲 - 每轮必须执行】
        ① 采纳分析（检查前轮建议是否被当前轮采纳）
        ② 策略分析 + 落盘（分析当前轮策略选择）
        ③ 建议注册（注册当前轮 Coach 建议，供下轮检测）
        
        Args:
            user_message: 用户输入
            session: 会话对象
            db: 数据库会话（必填，用于能力数据落盘）
        """
        if not self.fsm_state:
            raise RuntimeError("Session not initialized")
        if not self.user_id:
            raise RuntimeError("user_id is required for capability tracking")
        
        turn_start_time = datetime.utcnow()
        current_turn = self.fsm_state.turn_count + 1
        
        logger.info(f"=== Turn {current_turn} Start ===")
        logger.info(f"User: {user_message[:100]}...")
        
        # ========== Step 1: 记录用户消息 ==========
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "turn": current_turn,
            "timestamp": turn_start_time.isoformat(),
        })
        
        # ========== Step 2: Intent Gate ==========
        intent_result = await self.intent_gate.analyze(
            user_message=user_message,
            current_stage=self.fsm_state.current_stage,
            conversation_history=self.conversation_history,
            stage_config=self.fsm_engine.get_stage_config(self.fsm_state.current_stage),
        )
        
        # ========== Step 3: 并行 RAG + Compliance ==========
        rag_result, compliance_result = await asyncio.gather(
            self.rag_agent.retrieve(
                query=user_message,
                stage=self.fsm_state.current_stage,
                context=self._build_rag_context(),
            ),
            self.compliance_agent.check(
                message=user_message,
                stage=self.fsm_state.current_stage,
            ),
        )
        
        # ========== Step 4: NPC Agent ==========
        npc_result = await self.npc_agent.generate_response(
            user_message=user_message,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            intent_result=intent_result,
        )
        
        self.conversation_history.append({
            "role": "npc",
            "content": npc_result.response,
            "turn": current_turn,
            "timestamp": datetime.utcnow().isoformat(),
            "mood": npc_result.mood_after,
        })
        
        # ========== Step 5: Coach Agent ==========
        coach_result, _ = await self.coach_agent.generate_advice(
            user_message=user_message,
            npc_response=npc_result.response,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            rag_content=rag_result,
            compliance_result=compliance_result,
            strategy_analysis=None,
        )
        
        # ========== Step 6: Evaluator Agent ==========
        evaluator_result, strategy_analysis = await self.evaluator_agent.evaluate(
            user_message=user_message,
            npc_response=npc_result.response,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            stage_config=self.fsm_engine.get_stage_config(self.fsm_state.current_stage),
            compliance_result=compliance_result,
        )
        
        # ========== 【能力闭环 ①】采纳分析 - 检查前轮建议是否被采纳 ==========
        adoption_analysis = await self._execute_adoption_analysis(
            db=db,
            current_turn=current_turn,
            user_message=user_message,
            current_scores=evaluator_result.dimension_scores,
        )
        
        # ========== 【能力闭环 ②】策略分析 + 落盘 ==========
        strategy_analysis = await self._execute_strategy_analysis_and_save(
            db=db,
            current_turn=current_turn,
            user_message=user_message,
            npc_result=npc_result,
            evaluator_result=evaluator_result,
        )
        
        # ========== 【能力闭环 ③】建议注册 - 供下轮检测 ==========
        self._register_coach_suggestion(
            current_turn=current_turn,
            coach_result=coach_result,
            evaluator_result=evaluator_result,
            strategy_analysis=strategy_analysis,
        )
        
        # ========== Step 7: 生成策略级指导 ==========
        strategy_guidance = None
        if strategy_analysis and not strategy_analysis.is_optimal:
            strategy_guidance = self.coach_agent._generate_strategy_guidance(
                strategy_analysis, coach_result
            )
        
        # ========== Step 8: State Update ==========
        self.fsm_state, transition_decision = await self.state_updater.update(
            state=self.fsm_state,
            intent_result=intent_result,
            npc_result=npc_result,
            evaluator_result=evaluator_result,
            current_turn=current_turn,
        )
        self.fsm_state = self.fsm_engine.increment_turn(self.fsm_state)
        
        # ========== Step 9: 提交事务 ==========
        await db.commit()
        
        turn_end_time = datetime.utcnow()
        processing_time_ms = (turn_end_time - turn_start_time).total_seconds() * 1000
        
        turn_result = OrchestratorTurnResult(
            turn_number=current_turn,
            user_message=user_message,
            intent_result=intent_result,
            rag_result=rag_result,
            compliance_result=compliance_result,
            npc_result=npc_result,
            coach_result=coach_result,
            evaluator_result=evaluator_result,
            strategy_analysis=strategy_analysis.model_dump() if strategy_analysis else None,
            strategy_guidance=strategy_guidance.model_dump() if strategy_guidance else None,
            adoption_analysis=adoption_analysis.model_dump() if adoption_analysis else None,
            transition_decision=transition_decision,
            fsm_state_snapshot=self.fsm_state.model_copy(deep=True),
            processing_time_ms=processing_time_ms,
            timestamp=turn_end_time.isoformat(),
        )

        # Persist memory (best-effort, non-blocking)
        try:
            if not hasattr(self, "user_memory_service"):
                self.user_memory_service = UserMemoryService(org_id=session.org_id)
            content = (
        
                getattr(turn_result, "summary", None)
                or getattr(turn_result, "response_text", None)
                or npc_result.response
            )
            extracted_slots = getattr(turn_result.evaluator_result, "extracted_slots", [])
        # 1. 更新 UserStrategyProfile (会同时触发 CurriculumPlanner)
            self.user_memory_service.add_memory(
                user_id=self.user_id,
                content=content,
                meta={
                    "session_id": self.session_id,
                    "turn_number": current_turn,
                    "entities": entities,
            db=db,
            user_id=self.user_id
            mem = UserMemoryService(org_id=self.org_id)
            summary = (
                f"训练总结：采纳率={profile.adoption_rate:.2f}，有效采纳率={profile.effective_adoption_rate:.2f}。"
                f"下一训练重点：{recommended_focus.get('situation')} / {recommended_focus.get('strategy')}。"
            )
            mem.add_memory(user_id=self.user_id, content=summary, meta={"session_id": self.session_id})
        except Exception:
            pass
        
        logger.info(f"Session completed. Next focus: {recommended_focus.get('situation')}")

        # CRM event (best-effort)
        try:
            await CRMService.emit_event(
                "training_session_completed",
                {
        """
        【能力闭环 ①】采纳分析
        
        检查前 1-2 轮的 Coach 建议是否被当前轮采纳
        如果检测到采纳，写入 AdoptionRecord
        
        Returns:
            采纳分析结果（如果检测到采纳）
        """
                    "org_id": self.org_id,
                    "user_id": self.user_id,
                    "session_id": self.session_id,
        adoption_analysis = await self.adoption_tracker.analyze_adoption(
                    "effective_adoption_rate": profile.effective_adoption_rate,
                    "recommended_focus": recommended_focus,
                },
            )
        except Exception:
            pass
        
        
        if adoption_analysis:
            logger.info(
                f"[能力闭环] 采纳检测: suggestion={adoption_analysis.suggestion_id}, "
                f"style={adoption_analysis.adoption_style}, effective={adoption_analysis.is_effective}"
            )
        
        return adoption_analysis
        return {
            "user_id": self.user_id,
            "next_training_focus": recommended_focus,
            "overall_improvement": profile.effective_adoption_rate
        }

    # ========== 能力闭环核心方法 ==========
    
    async def _execute_adoption_analysis(
        """
        【能力闭环 ②】策略分析 + 落盘
        
        每一轮用户发言，必须产生 StrategyDecision
        没有 StrategyDecision = 该轮对能力系统无意义
        
        Returns:
            策略分析结果
        """
        # 获取上一轮 NPC 消息用于情境判断
        db: AsyncSession,
        current_turn: int,
        user_message: str,
        current_scores: Dict[str, float],
    ) -> Optional[AdoptionAnalysis]:
        if current_turn < 2:
        # 分析策略
            return None
        
        return await self.adoption_tracker.analyze_adoption(
            session_id=self.session_id,
            user_id=self.user_id,
            current_turn=current_turn,
        # 计算 NPC 情绪变化
        mood_change = npc_result.mood_after - npc_result.mood_before
        
        # 写入 StrategyDecision
        await self.strategy_analyzer.save_strategy_decision(
            db=db,
            session_id=self.session_id,
            user_id=self.user_id,
            turn_id=current_turn,
            analysis=strategy_analysis,
            npc_mood_change=mood_change,
            goal_progress=evaluator_result.goal_advanced,
            immediate_score=evaluator_result.overall_score,
        )
        
        logger.info(
            f"[能力闭环] 策略落盘: situation={strategy_analysis.situation_type}, "
            f"chosen={strategy_analysis.strategy_chosen}, optimal={strategy_analysis.is_optimal}"
        )
        
            user_message=user_message,
            current_scores=current_scores,
            db=db,
        )
    
    async def _execute_strategy_analysis_and_save(
        self,
        db: AsyncSession,
        current_turn: int,
        """
        【能力闭环 ③】建议注册
        
        注册当前轮 Coach 建议，供下轮检测采纳
        baseline_scores 代表建议出现时的能力状态
        
        Returns:
            suggestion_id
        """
        user_message: str,
        npc_result: NPCOutput,
        evaluator_result: EvaluatorOutput,
    ) -> StrategyAnalysis:
        # Fallback method if Evaluator didn't provide analysis
        prev_npc_message = ""
        for msg in reversed(self.conversation_history[:-1]):
            if msg.get("role") == "npc":
        
        logger.info(f"[能力闭环] 建议注册: suggestion_id={suggestion_id}, technique={coach_result.technique_name}")
        
                prev_npc_message = msg.get("content", "")
                break
        
        strategy_analysis = self.strategy_analyzer.analyze_strategy(
            user_message=user_message,
            npc_message=prev_npc_message,
            stage=self.fsm_state.current_stage,
        )
        
        return strategy_analysis
    
    def _register_coach_suggestion(
        self,
        current_turn: int,
        coach_result: CoachOutput,
        evaluator_result: EvaluatorOutput,
        strategy_analysis: StrategyAnalysis,
        return self.conversation_history.copy()
            session_id=self.session_id,
            turn_id=current_turn,
            coach_output=coach_result,
            baseline_scores=evaluator_result.dimension_scores,
            stage=self.fsm_state.current_stage.value,
        compliance_result: ComplianceOutput
    ):
        """记录合规违规日志"""
        try:
            high_risks = [f for f in compliance_result.risk_flags if f.severity == "high"]
            # 优先使用高风险，否则使用拦截原因
            risk_type = high_risks[0].risk_type if high_risks else "unknown"
            risk_reason = high_risks[0].risk_reason if high_risks else (compliance_result.block_reason or "Blocked by compliance")
            
            log_entry = ComplianceLog(
                id=str(uuid.uuid4()),
                org_id=session.org_id,
                session_id=self.session_id,
                turn_id=current_turn,
                original_text=scrub_pii(user_message),
                risk_type=risk_type,
                severity=RiskSeverity.HIGH,
                risk_reason=risk_reason[:255], # Truncate if too long
                action_taken="blocked"
            )
            db.add(log_entry)
            # Commit is handled by caller (Orchestrator usually commits at end, but here we commit to ensure log is saved even if crash)
            # Actually, process_turn commits at the end. But for blocked flow, we commit inside process_turn before return.
            # So here we just add.
        except Exception as e:
            logger.error(f"Failed to log compliance violation: {e}")
