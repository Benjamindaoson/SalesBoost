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
import uuid
import time
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
from app.security.prompt_guard import prompt_guard
from app.security.runtime_guard import runtime_guard, SecurityAction
from app.services.observability import trace_manager
from app.services.context_engine import ContextBuilder, ContextPolicy
from app.services.knowledge_engine import knowledge_engine
from app.schemas.trace import CallType, AgentDecision, SecurityEvent, KnowledgeEvidence, ContextManifest
from app.services.state_updater import StateUpdater
from app.services.adoption_tracker import AdoptionTracker
from app.services.strategy_analyzer import StrategyAnalyzer
from app.services.curriculum_planner import CurriculumPlanner
from app.services.memory_tiering import MemoryTierManager
from app.services.context_bus import ContextBus
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
        self.memory_manager = MemoryTierManager()
        self.context_bus = ContextBus()
        
        # 会话状态
        self.fsm_state: Optional[FSMState] = None
        self.conversation_history: list[Dict[str, Any]] = []
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
        
        # V3 开关
        self.v3_enabled = True # 默认开启 V3
    
    def set_v3_enabled(self, enabled: bool):
        self.v3_enabled = enabled
        logger.info(f"V3 mode set to: {enabled}")
    
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
        self.context_bus.reset()
        
        logger.info(f"Session initialized: {session_id}, user: {user_id}")
        return self.fsm_state

    async def process_interaction(
        self,
        user_message: str,
    ) -> OrchestratorTurnResult:
        """
        [Step 1] 处理即时交互 (User -> NPC)
        Fast Path 严格边界：Input Guard -> Context -> Intent -> RAG -> Output Guard -> NPC
        TTFS 统计仅包含此路径
        """
        if not self.fsm_state:
            raise RuntimeError("Session not initialized")
        
        turn_start_time = datetime.utcnow()
        current_turn = self.fsm_state.turn_count + 1
        trace_id = None

        # V3 Observability: 开始追踪 (Fast Path)
        if self.v3_enabled:
            trace_id = trace_manager.start_trace(self.session_id, current_turn, CallType.FAST_PATH)

        # ========== Step 0: Security Input Guard (P0-3) ==========
        if self.v3_enabled:
            action, sec_event = runtime_guard.check_input(user_message)
            if sec_event:
                trace_manager.record_security_event(trace_id, sec_event)
            if action == SecurityAction.BLOCK:
                logger.warning(f"Input blocked by Security Guard: {user_message}")
                raise ValueError(f"Security Alert: {sec_event.reason if sec_event else 'Input blocked'}")
        else:
            is_safe, reason = prompt_guard.detect(user_message)
            if not is_safe:
                logger.warning(f"Prompt injection blocked: {reason}")
                raise ValueError(f"Security Alert: {reason}")
            
        # 记录 User 消息
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "turn": current_turn,
            "timestamp": turn_start_time.isoformat(),
        })
        if self.user_id:
            self.memory_manager.add_episode(
                user_id=self.user_id,
                session_id=self.session_id or "unknown",
                content=user_message,
                metadata={"stage": self.fsm_state.current_stage.value},
            )
            if current_turn % 3 == 0:
                self.memory_manager.consolidate(self.user_id)

        # ========== Step 1: Context & Knowledge (P0-2, P0-4) ==========
        full_context = {}
        if self.v3_enabled:
            context_builder = ContextBuilder()
            context_builder.add_layer("system", "你是销售实战练习系统的 NPC。", priority=0)
            context_builder.add_layer("state", f"当前阶段: {self.fsm_state.current_stage.value}", priority=1)
            history_str = "\n".join([f"{m['role']}: {m['content']}" for m in self.conversation_history[-5:]])
            context_builder.add_layer("history", history_str, priority=2)
            if self.user_id:
                memory_hits = self.memory_manager.retrieve(self.user_id, user_message, top_k=3)
                memory_summary = self._format_memory_hits(memory_hits)
                if memory_summary:
                    context_builder.add_layer("memory", memory_summary, priority=2, source="memory")
            
            # Knowledge Retrieval (Fast Path 必需)
            start_t = time.time()
            evidences = knowledge_engine.retrieve(user_message)
            if self.v3_enabled:
                trace_manager.record_agent_call(trace_id, AgentDecision(
                    agent_name="KnowledgeRetriever",
                    action="retrieve",
                    latency_ms=(time.time() - start_t) * 1000,
                    reasoning=f"Retrieved {len(evidences)} items"
                ))

            for ev in evidences:
                trace_manager.record_evidence(trace_id, ev)
            
            knowledge_str = knowledge_engine.format_for_prompt(evidences)
            context_builder.add_layer("knowledge", knowledge_str, priority=3)
            
            full_context_str = context_builder.build()
            full_context = {"full_context": full_context_str}
            trace_manager.set_context_usage(trace_id, context_builder.get_usage())
        else:
            full_context = self._build_rag_context()

        # Step 2: Intent Gate
        start_t = time.time()
        intent_result = await self.intent_gate.analyze(
            user_message=user_message,
            current_stage=self.fsm_state.current_stage,
            conversation_history=self.conversation_history,
            stage_config=self.fsm_engine.get_stage_config(self.fsm_state.current_stage),
        )
        self.context_bus.publish("intent", self._dump_model(intent_result))
        self.context_bus.publish("state", {"stage": self.fsm_state.current_stage.value})
        if self.v3_enabled:
            trace_manager.record_agent_call(trace_id, AgentDecision(
                agent_name="IntentGate",
                action="analyze",
                latency_ms=(time.time() - start_t) * 1000,
                model_used="gpt-3.5-turbo"
            ))

        # Step 3: RAG (Lite) + Compliance Check
        # Fast Path 中只做轻量 RAG (Context Assembly 已做一部分) 和 基础合规
        start_t = time.time()
        # 注意：这里的 RAG 可能是冗余的，如果 ContextBuilder 已经检索了知识
        # 为了兼容现有架构，我们只在 V3 关闭时调用完整 RAG，或者在 V3 中仅作补充
        # 这里简化处理：V3 模式下 rag_agent 复用 context
        rag_context = {
            **full_context,
            **self.context_bus.view_for("rag"),
        }
        rag_result, compliance_result = await asyncio.gather(
            self.rag_agent.retrieve(
                query=user_message,
                stage=self.fsm_state.current_stage,
                context=rag_context,
            ),
            self.compliance_agent.check(
                message=user_message,
                stage=self.fsm_state.current_stage,
            ),
        )
        if self.v3_enabled:
            trace_manager.record_agent_call(trace_id, AgentDecision(
                agent_name="ComplianceCheck", # RAG is implicit in Context
                action="check",
                latency_ms=(time.time() - start_t) * 1000
            ))

        # Step 4: NPC Generation
        start_t = time.time()
        npc_result = await self.npc_agent.generate_response(
            user_message=user_message,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            intent_result=intent_result,
        )
        
        # ========== Step 5: Security Output Guard (P0-3) ==========
        if self.v3_enabled:
            sec_action, modified_response, sec_event = runtime_guard.check_output(npc_result.response)
            if sec_event:
                trace_manager.record_security_event(trace_id, sec_event)
                # 如果是改写/拦截，覆盖 NPC 回复
                npc_result.response = modified_response
                # 记录修改动作
                trace_manager.record_agent_call(trace_id, AgentDecision(
                    agent_name="RuntimeGuard",
                    action=sec_action,
                    reasoning=sec_event.reason
                ))

        if self.v3_enabled:
            trace_manager.record_agent_call(trace_id, AgentDecision(
                agent_name="NPC",
                action="generate",
                latency_ms=(time.time() - start_t) * 1000,
                model_used="gpt-4-turbo"
            ))

        # 记录 NPC 消息
        self.conversation_history.append({
            "role": "npc",
            "content": npc_result.response,
            "turn": current_turn,
            "timestamp": datetime.utcnow().isoformat(),
            "mood": npc_result.mood_after,
        })
        
        # TTFS 截止点 (NPC 回复准备好返回)
        end_time = datetime.utcnow()
        processing_time_ms = (end_time - turn_start_time).total_seconds() * 1000

        if self.v3_enabled:
            trace = trace_manager.get_trace(trace_id)
            if trace:
                trace.ttfs_ms = processing_time_ms
                trace_manager.complete_trace(trace_id, status="success")

        return OrchestratorTurnResult(
            turn_number=current_turn,
            user_message=user_message,
            intent_result=intent_result,
            rag_result=rag_result,
            compliance_result=compliance_result,
            npc_result=npc_result,
            coach_result=None,
            evaluator_result=None,
            fsm_state_snapshot=self.fsm_state.model_copy(deep=True),
            processing_time_ms=processing_time_ms,
            timestamp=turn_start_time.isoformat(),
            trace_id=trace_id
        )

    async def process_analysis(
        self,
        turn_result: OrchestratorTurnResult,
        db: AsyncSession,
    ) -> OrchestratorTurnResult:
        """
        [Step 2] 后台分析 (Coach, Eval, Strategy, DB)
        Slow Path: 独立 Trace，不影响 TTFS
        """
        current_turn = turn_result.turn_number
        user_message = turn_result.user_message
        npc_result = turn_result.npc_result
        rag_result = turn_result.rag_result
        compliance_result = turn_result.compliance_result
        
        # Slow Path 使用新的 trace_id (或作为子 span，这里简化为独立 trace)
        trace_id = None
        if self.v3_enabled:
            trace_id = trace_manager.start_trace(self.session_id, current_turn, CallType.SLOW_PATH)
        
        start_slow_t = time.time()
        
        # Step 5: Coach Agent
        start_t = time.time()
        coach_result, _ = await self.coach_agent.generate_advice(
            user_message=user_message,
            npc_response=npc_result.response,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            rag_content=rag_result,
            compliance_result=compliance_result,
            strategy_analysis=None,
        )
        if self.v3_enabled and trace_id:
            trace_manager.record_agent_call(trace_id, AgentDecision(
                agent_name="Coach",
                action="generate_advice",
                latency_ms=(time.time() - start_t) * 1000
            ))
        
        # Step 6: Evaluator Agent
        start_t = time.time()
        evaluator_result, strategy_analysis = await self.evaluator_agent.evaluate(
            user_message=user_message,
            npc_response=npc_result.response,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            stage_config=self.fsm_engine.get_stage_config(self.fsm_state.current_stage),
            compliance_result=compliance_result,
        )
        if self.v3_enabled and trace_id:
            trace_manager.record_agent_call(trace_id, AgentDecision(
                agent_name="Evaluator",
                action="evaluate",
                latency_ms=(time.time() - start_t) * 1000
            ))
        
        # Step 7: 能力闭环 (Adoption, Strategy, Suggestion)
        # 这些是 DB 操作，耗时较短但属 Slow Path
        start_t = time.time()
        adoption_analysis = await self._execute_adoption_analysis(
            db=db,
            current_turn=current_turn,
            user_message=user_message,
            current_scores=evaluator_result.dimension_scores,
        )
        
        strategy_analysis_result = await self._execute_strategy_analysis_and_save(
            db=db,
            current_turn=current_turn,
            user_message=user_message,
            npc_result=npc_result,
            evaluator_result=evaluator_result,
        )
        
        self._register_coach_suggestion(
            current_turn=current_turn,
            coach_result=coach_result,
            evaluator_result=evaluator_result,
            strategy_analysis=strategy_analysis_result,
        )
        
        # Step 8: Strategy Guidance
        strategy_guidance = None
        if strategy_analysis_result and not strategy_analysis_result.is_optimal:
            strategy_guidance = self.coach_agent._generate_strategy_guidance(
                strategy_analysis_result, coach_result
            )
            
        # Step 9: State Update
        self.fsm_state, transition_decision = await self.state_updater.update(
            state=self.fsm_state,
            intent_result=turn_result.intent_result,
            npc_result=npc_result,
            evaluator_result=evaluator_result,
            current_turn=current_turn,
        )
        self.fsm_state = self.fsm_engine.increment_turn(self.fsm_state)
        
        if self.v3_enabled and trace_id:
             trace_manager.record_agent_call(trace_id, AgentDecision(
                agent_name="CapabilityLoop",
                action="persist_and_update",
                latency_ms=(time.time() - start_t) * 1000
            ))

        # 更新 TurnResult
        turn_result.coach_result = coach_result
        turn_result.evaluator_result = evaluator_result
        turn_result.strategy_analysis = strategy_analysis_result.model_dump() if strategy_analysis_result else None
        turn_result.strategy_guidance = strategy_guidance.model_dump() if strategy_guidance else None
        turn_result.adoption_analysis = adoption_analysis.model_dump() if adoption_analysis else None
        turn_result.transition_decision = transition_decision
        turn_result.fsm_state_snapshot = self.fsm_state.model_copy(deep=True)
        
        if self.v3_enabled and trace_id:
            slow_latency = (time.time() - start_slow_t) * 1000
            trace_manager.get_trace(trace_id).total_latency_ms = slow_latency
            trace_manager.complete_trace(trace_id, status="success")
            logger.info(f"Slow path completed for {trace_id} in {slow_latency:.2f}ms")
        
        return turn_result

    def dispose(self):
        """清理资源 (Agent Lifecycle P1)"""
        self.conversation_history.clear()
        self.fsm_state = None
        # 清理子 Agent 状态（如果它们有）
        if hasattr(self.coach_agent, "dispose"):
            self.coach_agent.dispose()
        if hasattr(self.evaluator_agent, "dispose"):
            self.evaluator_agent.dispose()
        # 解除引用
        self.npc_agent = None
        self.coach_agent = None
        self.evaluator_agent = None
        logger.info(f"Orchestrator disposed for session {self.session_id}")

    # Deprecated monolithic method
    async def process_turn(self, *args, **kwargs):
        raise NotImplementedError("Use process_interaction and process_analysis instead")

    # ========== 能力闭环核心方法 ==========
    
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
        
        Returns:
            采纳分析结果（如果检测到采纳）
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
                f"[能力闭环] 采纳检测: suggestion={adoption_analysis.suggestion_id}, "
                f"style={adoption_analysis.adoption_style}, effective={adoption_analysis.is_effective}"
            )
        
        return adoption_analysis
    
    async def _execute_strategy_analysis_and_save(
        self,
        db: AsyncSession,
        current_turn: int,
        user_message: str,
        npc_result: NPCOutput,
        evaluator_result: EvaluatorOutput,
    ) -> StrategyAnalysis:
        """
        【能力闭环 ②】策略分析 + 落盘
        
        每一轮用户发言，必须产生 StrategyDecision
        没有 StrategyDecision = 该轮对能力系统无意义
        
        Returns:
            策略分析结果
        """
        # 获取上一轮 NPC 消息用于情境判断
        prev_npc_message = ""
        for msg in reversed(self.conversation_history[:-1]):
            if msg.get("role") == "npc":
                prev_npc_message = msg.get("content", "")
                break
        
        # 分析策略
        strategy_analysis = self.strategy_analyzer.analyze_strategy(
            user_message=user_message,
            npc_message=prev_npc_message,
            stage=self.fsm_state.current_stage,
        )
        
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
        
        return strategy_analysis
    
    def _register_coach_suggestion(
        self,
        current_turn: int,
        coach_result: CoachOutput,
        evaluator_result: EvaluatorOutput,
        strategy_analysis: Any,
    ) -> str:
        """
        【能力闭环 ③】建议注册
        
        注册当前轮 Coach 建议，供下轮检测采纳
        baseline_scores 代表建议出现时的能力状态
        
        Returns:
            suggestion_id
        """
        situation_type = None
        if strategy_analysis:
            if hasattr(strategy_analysis, "situation_type"):
                st = strategy_analysis.situation_type
                situation_type = st.value if hasattr(st, "value") else str(st)
            elif isinstance(strategy_analysis, dict):
                situation_type = strategy_analysis.get("situation_type")

        suggestion_id = self.adoption_tracker.register_suggestion(
            session_id=self.session_id,
            turn_id=current_turn,
            coach_output=coach_result,
            baseline_scores=evaluator_result.dimension_scores,
            stage=self.fsm_state.current_stage.value,
            situation_type=situation_type,
        )
        
        logger.info(
            f"[能力闭环] 建议注册: suggestion_id={suggestion_id}, "
            f"technique={coach_result.technique_name}"
        )
        
        return suggestion_id
    
    def _build_rag_context(self) -> Dict[str, Any]:
        """构建 RAG 检索上下文"""
        return {
            "conversation_history": self.conversation_history.copy(),
            "current_stage": self.fsm_state.current_stage.value if self.fsm_state else None,
            "scenario": self.scenario_config.name if self.scenario_config else None,
        }

    def _format_memory_hits(self, memory_hits: Dict[str, Any]) -> str:
        if not memory_hits:
            return ""
        lines = []
        for tier in ("semantic", "procedural", "episodic"):
            hits = memory_hits.get(tier, [])
            if not hits:
                continue
            lines.append(f"[{tier.upper()}]")
            for hit in hits:
                lines.append(f"- {hit.content}")
        return "\n".join(lines)

    def _dump_model(self, obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return obj
    
    def is_session_completed(self) -> bool:
        """
        检查会话是否完成
        
        Returns:
            True 如果会话已完成（到达 COMPLETED 阶段或满足完成条件）
        """
        if not self.fsm_state:
            return False
        
        # 检查是否到达完成阶段
        if self.fsm_state.current_stage == SalesStage.COMPLETED:
            return True
        
        # 检查是否所有目标都达成（如果有目标配置）
        if hasattr(self.scenario_config, 'completion_criteria'):
            # 这里可以根据实际配置判断
            pass
        
        return False
    
    async def complete_session(
        self,
        db: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        """
        完成会话并生成课程推荐
        
        Args:
            db: 数据库会话
            
        Returns:
            包含 next_training_focus 和 overall_improvement 的字典
        """
        if not self.user_id:
            logger.warning("Cannot complete session: user_id not set")
            return None
        
        try:
            # 生成课程计划
            curriculum_plan = await self.curriculum_planner.generate_curriculum(
                db=db,
                user_id=self.user_id,
                max_focus_items=3,
            )
            
            # 获取用户策略画像（用于计算整体改进）
            profile = await StrategyAnalyzer.get_user_strategy_profile(db, self.user_id)
            
            # 提取推荐重点
            recommended_focus = None
            if curriculum_plan.next_training_plan:
                first_focus = curriculum_plan.next_training_plan[0]
                recommended_focus = {
                    "stage": first_focus.stage,
                    "situation": first_focus.focus_situation,
                    "strategy": first_focus.focus_strategy,
                    "difficulty": first_focus.difficulty,
                }
            
            result = {
                "user_id": self.user_id,
                "next_training_focus": recommended_focus,
                "overall_improvement": profile.get("effective_adoption_rate", 0.0) if profile else 0.0,
                "curriculum_reasoning": curriculum_plan.reasoning,
                "expected_improvement": curriculum_plan.expected_improvement,
            }
            
            logger.info(
                f"Session completed. Next focus: {recommended_focus.get('situation') if recommended_focus else 'None'}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error completing session: {e}", exc_info=True)
            return None
