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

from app.schemas.fsm import FSMState, SalesStage
from app.schemas.agent_outputs import (
    IntentGateOutput,
    NPCOutput,
    CoachOutput,
    EvaluatorOutput,
    RAGOutput,
    ComplianceOutput,
    OrchestratorTurnResult,
)
from app.schemas.strategy import StrategyAnalysis, AdoptionAnalysis
from app.fsm.engine import FSMEngine
from app.fsm.decision_engine import StateUpdater
from app.agents.intent_gate import IntentGateAgent
from app.agents.npc_agent import NPCAgent
from app.agents.coach_agent import CoachAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.rag_agent import RAGAgent
from app.agents.compliance_agent import ComplianceAgent
from app.services.adoption_tracker import AdoptionTracker
from app.services.strategy_analyzer import StrategyAnalyzer
from app.services.curriculum_planner import CurriculumPlanner
from app.models.config_models import ScenarioConfig, CustomerPersona
from app.models.runtime_models import Session

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

        logger.info("Session initialized: %s, user: %s", session_id, user_id)
        return self.fsm_state

    async def process_turn(
        self,
        user_message: str,
        session: Session,
        db: AsyncSession,
    ) -> OrchestratorTurnResult:
        """
        处理单轮对话 - 包含完整能力闭环

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

        logger.info("=== Turn %s Start ===", current_turn)
        logger.info("User: %s...", user_message[:100])

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

        # ========== Step 7: State Update ==========
        self.fsm_state, transition_decision = await self.state_updater.update(
            state=self.fsm_state,
            intent_result=intent_result,
            npc_result=npc_result,
            evaluator_result=evaluator_result,
            current_turn=current_turn,
        )
        self.fsm_state = self.fsm_engine.increment_turn(self.fsm_state)

        # ========== Step 8: 能力闭环 ==========
        adoption_analysis = await self._execute_adoption_analysis(
            db=db,
            current_turn=current_turn,
            user_message=user_message,
            current_scores=evaluator_result.dimension_scores,
        )

        strategy_analysis = await self._execute_strategy_analysis_and_save(
            db=db,
            current_turn=current_turn,
            user_message=user_message,
            npc_result=npc_result,
            evaluator_result=evaluator_result,
            strategy_analysis=strategy_analysis,
        )

        self._register_coach_suggestion(
            current_turn=current_turn,
            coach_result=coach_result,
            evaluator_result=evaluator_result,
            strategy_analysis=strategy_analysis,
        )

        strategy_guidance = None
        if strategy_analysis and not strategy_analysis.is_optimal:
            strategy_guidance = self.coach_agent._generate_strategy_guidance(
                strategy_analysis,
                coach_result,
            )

        # ========== Step 9: 提交事务 ==========
        await db.commit()

        turn_end_time = datetime.utcnow()
        processing_time_ms = (turn_end_time - turn_start_time).total_seconds() * 1000

        return OrchestratorTurnResult(
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

    def _build_rag_context(self) -> Dict[str, Any]:
        """构建 RAG 检索上下文"""
        return {
            "scenario": {
                "id": self.scenario_config.id,
                "name": self.scenario_config.name,
                "product_category": self.scenario_config.product_category,
                "background": self.scenario_config.scenario_background,
                "sales_goal": self.scenario_config.sales_goal,
            },
            "persona": {
                "id": self.customer_persona.id,
                "name": self.customer_persona.name,
                "occupation": self.customer_persona.occupation,
                "traits": self.customer_persona.personality_traits,
                "concerns": self.customer_persona.main_concerns,
            },
        }

    async def _execute_adoption_analysis(
        self,
        db: AsyncSession,
        current_turn: int,
        user_message: str,
        current_scores: Dict[str, float],
    ) -> Optional[AdoptionAnalysis]:
        """
        【能力闭环 ①】采纳分析

        检查前 1-2 轮的 Coach 建议是否被当前轮采纳
        如果检测到采纳，写入 AdoptionRecord
        """
        if current_turn < 2:
            return None

        adoption_analysis = await self.adoption_tracker.analyze_adoption(
            session_id=self.session_id,
            user_id=self.user_id,
            current_turn=current_turn,
            user_message=user_message,
            current_scores=current_scores,
            db=db,
        )

        if adoption_analysis:
            logger.info(
                "[能力闭环] 采纳检测: suggestion=%s, style=%s, effective=%s",
                adoption_analysis.suggestion_id,
                adoption_analysis.adoption_style,
                adoption_analysis.is_effective,
            )

        return adoption_analysis

    async def _execute_strategy_analysis_and_save(
        self,
        db: AsyncSession,
        current_turn: int,
        user_message: str,
        npc_result: NPCOutput,
        evaluator_result: EvaluatorOutput,
        strategy_analysis: Optional[StrategyAnalysis],
    ) -> StrategyAnalysis:
        """
        【能力闭环 ②】策略分析 + 落盘

        每一轮用户发言，必须产生 StrategyDecision
        没有 StrategyDecision = 该轮对能力系统无意义
        """
        analysis = strategy_analysis
        if not analysis:
            prev_npc_message = ""
            for msg in reversed(self.conversation_history[:-1]):
                if msg.get("role") == "npc":
                    prev_npc_message = msg.get("content", "")
                    break
            analysis = self.strategy_analyzer.analyze_strategy(
                user_message=user_message,
                npc_message=prev_npc_message,
                stage=self.fsm_state.current_stage,
            )

        mood_change = npc_result.mood_after - npc_result.mood_before

        await self.strategy_analyzer.save_strategy_decision(
            db=db,
            session_id=self.session_id,
            user_id=self.user_id,
            turn_id=current_turn,
            analysis=analysis,
            npc_mood_change=mood_change,
            goal_progress=evaluator_result.goal_advanced,
            immediate_score=evaluator_result.overall_score,
        )

        logger.info(
            "[能力闭环] 策略落盘: situation=%s, chosen=%s, optimal=%s",
            analysis.situation_type,
            analysis.strategy_chosen,
            analysis.is_optimal,
        )

        return analysis

    def _register_coach_suggestion(
        self,
        current_turn: int,
        coach_result: CoachOutput,
        evaluator_result: EvaluatorOutput,
        strategy_analysis: StrategyAnalysis,
    ) -> None:
        """
        【能力闭环 ③】建议注册

        注册当前轮 Coach 建议，供下轮检测采纳
        baseline_scores 代表建议出现时的能力状态
        """
        if not strategy_analysis:
            return

        suggestion_id = self.adoption_tracker.register_suggestion(
            session_id=self.session_id,
            turn_id=current_turn,
            coach_output=coach_result,
            baseline_scores=evaluator_result.dimension_scores,
            stage=self.fsm_state.current_stage.value,
            situation_type=strategy_analysis.situation_type,
        )

        logger.info(
            "[能力闭环] 建议注册: suggestion_id=%s, technique=%s",
            suggestion_id,
            coach_result.technique_name,
        )

    def is_session_completed(self) -> bool:
        """判断会话是否完成"""
        if not self.fsm_state:
            return False
        if self.fsm_state.current_stage == SalesStage.COMPLETED:
            return True
        return self.fsm_state.turn_count >= self.scenario_config.max_turns

    async def complete_session(self, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """
        完成会话并生成训练计划
        """
        if not self.user_id:
            return None

        profile = await self.curriculum_planner.update_user_profile(
            db=db,
            user_id=self.user_id,
        )
        await db.commit()

        return {
            "user_id": self.user_id,
            "next_training_focus": profile.recommended_focus,
            "overall_improvement": profile.effective_adoption_rate,
        }
