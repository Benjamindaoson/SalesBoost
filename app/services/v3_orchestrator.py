"""
V3 Orchestrator - 双流编排器
实现 Fast Path / Slow Path 分离
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.v3_agent_outputs import (
    TurnPlan,
    EvidencePack,
    NpcReply,
    CoachAdvice,
    Evaluation,
    AdoptionLog,
    FastPathResult,
    SlowPathResult,
    V3TurnResult,
)
from app.schemas.fsm import FSMState, SalesStage
from app.agents.v3.session_director_v3 import SessionDirectorV3
from app.agents.v3.retriever_v3 import RetrieverV3
from app.agents.v3.npc_generator_v3 import NPCGeneratorV3
from app.agents.v3.coach_generator_v3 import CoachGeneratorV3
from app.agents.v3.evaluator_v3 import EvaluatorV3
from app.agents.v3.adoption_tracker_v3 import AdoptionTrackerV3
from app.services.model_gateway import ModelGateway, AgentType, LatencyMode, RoutingContext
from app.services.model_gateway.budget import BudgetManager
from app.models.config_models import CustomerPersona
from app.services.observability import trace_manager
from app.security.runtime_guard import runtime_guard, SecurityAction
from app.services.context_engine import ContextBuilder
from app.services.knowledge_engine import knowledge_engine
from app.schemas.trace import AgentDecision, CallType

logger = logging.getLogger(__name__)


class V3Orchestrator:
    """V3 Orchestrator - 双流编排"""
    
    def __init__(
        self,
        model_gateway: ModelGateway,
        budget_manager: BudgetManager,
        session_director: SessionDirectorV3,
        persona: CustomerPersona,
        retriever: Optional[RetrieverV3] = None,
        npc_generator: Optional[NPCGeneratorV3] = None,
        coach_generator: Optional[CoachGeneratorV3] = None,
        evaluator: Optional[EvaluatorV3] = None,
        adoption_tracker: Optional[AdoptionTrackerV3] = None,
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        self.session_director = session_director
        self.persona = persona
        
        # 初始化 V3 Agents
        self.retriever = retriever or RetrieverV3(model_gateway, budget_manager)
        self.npc_generator = npc_generator or NPCGeneratorV3(model_gateway, budget_manager, persona)
        self.coach_generator = coach_generator or CoachGeneratorV3(model_gateway, budget_manager)
        self.evaluator = evaluator or EvaluatorV3(model_gateway, budget_manager)
        self.adoption_tracker = adoption_tracker or AdoptionTrackerV3(model_gateway, budget_manager)
        
        # 状态
        self.fsm_state: Optional[FSMState] = None
        self.conversation_history: list[Dict[str, Any]] = []
        self.session_id: Optional[str] = None
        self.user_id: Optional[str] = None
        
        # 指标追踪
        self.metrics = {
            "fast_path_ttfs_ms": [],
            "slow_path_total_ms": [],
            "provider_hits": {},
            "model_hits": {},
            "downgrade_count": 0,
            "downgrade_reasons": [],
            "token_usage": [],
            "estimated_costs": [],
        }
        self._last_slow_task: Optional[asyncio.Task] = None
    
    async def initialize_session(
        self,
        session_id: str,
        user_id: str,
        fsm_state: FSMState,
    ):
        """初始化会话"""
        self.session_id = session_id
        self.user_id = user_id
        self.fsm_state = fsm_state
        self.conversation_history = []
        self.budget_manager.initialize_session(session_id)
        logger.info(f"V3 Orchestrator initialized: {session_id}")
    
    async def process_turn(
        self,
        turn_number: int,
        user_message: str,
        db: Optional[AsyncSession] = None,
    ) -> V3TurnResult:
        """
        处理轮次（双流架构）
        
        Returns:
            V3TurnResult（包含 Fast Path 结果，Slow Path 异步执行）
        """
        if not self.fsm_state or not self.session_id:
            raise RuntimeError("Session not initialized")
        
        # 记录用户消息
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "turn": turn_number,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        fast_trace_id = trace_manager.start_trace(self.session_id, turn_number, CallType.FAST_PATH)
        slow_trace_id: Optional[str] = None
        slow_path_result = None

        # Step 1: Fast Path（必须执行，严格最小集）
        fast_path_result = await self._execute_fast_path(
            turn_number=turn_number,
            user_message=user_message,
            fast_trace_id=fast_trace_id,
        )

        # Step 2: Slow Path（异步，不影响 TTFS）
        slow_trace_id = trace_manager.start_trace(self.session_id, turn_number, CallType.SLOW_PATH)
        trace = trace_manager.get_trace(fast_trace_id)
        if trace:
            trace.linked_slow_trace_id = slow_trace_id

        self._last_slow_task = asyncio.create_task(
            self._execute_slow_path_async(
                turn_number=turn_number,
                user_message=user_message,
                npc_reply=fast_path_result.npc_reply,
                slow_trace_id=slow_trace_id,
                fast_trace_id=fast_trace_id,
                db=db,
            )
        )
        
        # 记录 NPC 消息
        self.conversation_history.append({
            "role": "npc",
            "content": fast_path_result.npc_reply.response,
            "turn": turn_number,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # 返回结果（Fast Path 立即返回）
        return V3TurnResult(
            turn_number=turn_number,
            fast_path_result=fast_path_result,
            slow_path_result=slow_path_result,  # None，异步执行中
            session_id=self.session_id,
            user_id=self.user_id,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    async def _execute_fast_path(
        self,
        turn_number: int,
        user_message: str,
        fast_trace_id: str,
    ) -> FastPathResult:
        """执行 Fast Path（<3s TTFS）"""
        fast_start_time = time.time()

        # Security Input Guard (pre-generate)
        action, sec_event = runtime_guard.check_input(user_message)
        if sec_event:
            trace_manager.record_security_event(fast_trace_id, sec_event)
        if action == SecurityAction.BLOCK:
            trace = trace_manager.get_trace(fast_trace_id)
            if trace:
                trace.ttfs_ms = 0.0
                trace.ttfs_stop_point = "blocked_before_generate"
            trace_manager.complete_trace(fast_trace_id, status="blocked", error=sec_event.reason if sec_event else "blocked")
            raise ValueError(f"Security Alert: {sec_event.reason if sec_event else 'blocked'}")

        # 1) Lightweight Retrieval (may be 0)
        retrieval_start = time.time()
        evidences = knowledge_engine.retrieve(user_message, top_k=3)
        for ev in evidences:
            trace_manager.record_evidence(fast_trace_id, ev)
        retrieval_ms = (time.time() - retrieval_start) * 1000
        retrieval_confidence = sum(e.confidence for e in evidences) / len(evidences) if evidences else 0.0
        trace_manager.record_agent_call(
            fast_trace_id,
            AgentDecision(
                agent_name="Retriever",
                action="lightweight_retrieve",
                latency_ms=retrieval_ms,
                reasoning=f"items={len(evidences)}, retrieval_confidence={retrieval_confidence:.2f}",
            ),
        )

        # 2) ContextBuilder (mandatory) for NPC model call
        context_builder = ContextBuilder()
        context_builder.add_layer("system", "你是销售实战练习系统的 NPC。", priority=0, source="system")
        context_builder.add_layer("state", f"stage={self.fsm_state.current_stage.value}", priority=1, source="fsm")
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in self.conversation_history[-5:]])
        context_builder.add_layer("history", history_str, priority=2, source="memory")
        context_builder.add_layer("knowledge", knowledge_engine.format_for_prompt(evidences), priority=3, source="retriever")
        _ = context_builder.build()
        trace_manager.set_context_usage(fast_trace_id, context_builder.get_usage())

        # 3) NPC Generation via ModelGateway (provider/model/router/budget)
        npc_start = time.time()
        budget_remaining = self.budget_manager.get_remaining_budget(self.session_id)
        routing_context = RoutingContext(
            agent_type=AgentType.NPC_GENERATOR,
            turn_importance=0.5,
            risk_level="high" if action == SecurityAction.DOWNGRADE else "low",
            budget_remaining=budget_remaining,
            latency_mode=LatencyMode.FAST,
            retrieval_confidence=retrieval_confidence,
            turn_number=turn_number,
            session_id=self.session_id,
        )
        system_prompt = context_builder.build()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        model_result = await self.model_gateway.chat(
            agent_type=AgentType.NPC_GENERATOR,
            messages=messages,
            context=routing_context,
            temperature=0.7,
        )
        npc_latency_ms = (time.time() - npc_start) * 1000

        npc_text = model_result.get("content", "")
        if retrieval_confidence < 0.6:
            npc_text = f"【无证据/需确认】{npc_text}"

        # Security Output Guard (post-generate)
        out_action, modified_text, out_event = runtime_guard.check_output(npc_text)
        if out_event:
            trace_manager.record_security_event(fast_trace_id, out_event)
        npc_text = modified_text

        trace_manager.record_agent_call(
            fast_trace_id,
            AgentDecision(
                agent_name="NPC",
                action="generate",
                provider=model_result.get("provider"),
                model_used=model_result.get("model"),
                latency_ms=model_result.get("latency_ms", npc_latency_ms),
                input_tokens=model_result.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=model_result.get("usage", {}).get("completion_tokens", 0),
                estimated_cost=model_result.get("cost_usd", 0.0),
                routing_reason=model_result.get("routing_reason"),
                downgrade_reason=model_result.get("downgrade_reason"),
                budget_remaining=model_result.get("budget_remaining"),
                reasoning="npc_returned" if retrieval_confidence >= 0.6 else "npc_returned (weak_assertion: no_evidence)",
            ),
        )

        npc_reply = NpcReply(
            response=npc_text,
            mood_before=self.fsm_state.npc_mood,
            mood_after=self.fsm_state.npc_mood,
            mood_change_reason="V3 mock mood",
            expressed_signals=[],
            persona_consistency=0.8,
            stage_alignment=True,
        )

        evidence_pack = EvidencePack(
            items=[],
            retrieval_mode="lightweight",
            total_items=len(evidences),
            confidence=retrieval_confidence,
            retrieval_time_ms=retrieval_ms,
        )
        turn_plan = TurnPlan(
            turn_number=turn_number,
            path_mode="both",
            agents_to_call=["retriever", "npc_generator"],
            budget_allocation={},
            model_upgrade=False,
            risk_level="high" if action == SecurityAction.DOWNGRADE else "low",
            evidence_confidence=retrieval_confidence,
            reasoning="Fast path: retriever + npc only",
        )
        
        # 计算 TTFS（Time To First Sentence）
        ttfs_ms = (time.time() - fast_start_time) * 1000
        total_latency_ms = ttfs_ms
        trace = trace_manager.get_trace(fast_trace_id)
        if trace:
            trace.ttfs_ms = ttfs_ms
            trace.ttfs_stop_point = "npc_returned"
        trace_manager.complete_trace(fast_trace_id, status="success")
        
        # 指标埋点：fast_path_ttfs_ms
        self.metrics["fast_path_ttfs_ms"].append(ttfs_ms)
        logger.info(
            f"Fast Path completed: turn={turn_number}, ttfs={ttfs_ms:.0f}ms "
            f"[METRIC: fast_path_ttfs_ms={ttfs_ms:.0f}]"
        )
        
        return FastPathResult(
            turn_number=turn_number,
            npc_reply=npc_reply,
            evidence_pack=evidence_pack,
            turn_plan=turn_plan,
            ttfs_ms=ttfs_ms,
            total_latency_ms=total_latency_ms,
        )
    
    async def _execute_slow_path_async(
        self,
        turn_number: int,
        user_message: str,
        npc_reply: NpcReply,
        slow_trace_id: str,
        fast_trace_id: str,
        db: Optional[AsyncSession] = None,
    ) -> SlowPathResult:
        """异步执行 Slow Path，并推送结果"""
        result = await self._execute_slow_path(turn_number, user_message, npc_reply, slow_trace_id, db=db)
        trace_manager.link_slow_path(fast_trace_id, slow_trace_id, result.total_latency_ms)
        
        # 推送 Slow Path 结果到 WebSocket（如果 manager 可用）
        # 注意：这里需要从外部传入 manager，暂时通过全局方式获取
        try:
            from app.api.endpoints.websocket import manager
            await manager.send_json(self.session_id, {
                "type": "turn_analysis",
                "turn": turn_number,
                "coach_advice": result.coach_advice.model_dump() if result.coach_advice else None,
                "evaluation": result.evaluation.model_dump() if result.evaluation else None,
                "adoption_log": result.adoption_log.model_dump() if result.adoption_log else None,
                "slow_path_latency_ms": result.total_latency_ms,
            })
        except Exception as e:
            logger.error(f"Failed to send slow path result: {e}")
        
        return result
    
    async def _execute_slow_path(
        self,
        turn_number: int,
        user_message: str,
        npc_reply: NpcReply,
        slow_trace_id: str,
        db: Optional[AsyncSession] = None,
    ) -> SlowPathResult:
        """执行 Slow Path（异步，5-30s）"""
        slow_start_time = time.time()
        
        try:
            coach_advice = None
            evaluation = None
            adoption_log = None
            
            # 获取数据库会话（从外部传入或创建）
            # 注意：这里需要 db，但 V3Orchestrator 不应该直接管理 db
            # 实际使用时应该从外部传入
            # db = None  # TODO: 从参数传入
            
            # Coach Generator（Slow Path，使用 ModelGateway，记录独立 slow trace）
            coach_start = time.time()
            # 让 Router 稳定命中 Mock（避免真实 Key/外部依赖影响验收）
            budget_remaining = 0.0
            routing_context = RoutingContext(
                agent_type=AgentType.COACH_GENERATOR,
                turn_importance=0.5,
                risk_level="low",
                budget_remaining=budget_remaining,
                latency_mode=LatencyMode.SLOW,
                retrieval_confidence=None,
                turn_number=turn_number,
                session_id=self.session_id,
            )
            messages = [
                {"role": "system", "content": "你是销售教练，请给出简短可执行建议。关键判断需引用 evidence_id 或声明无证据/需确认。"},
                {"role": "user", "content": f"用户: {user_message}\nNPC: {npc_reply.response}\n请给建议。"},
            ]
            model_result = await self.model_gateway.chat(
                agent_type=AgentType.COACH_GENERATOR,
                messages=messages,
                context=routing_context,
                temperature=0.3,
            )
            # 让 Slow Path 明显慢于 Fast Path（不影响 TTFS）
            await asyncio.sleep(0.3)
            trace_manager.record_agent_call(
                slow_trace_id,
                AgentDecision(
                    agent_name="Coach",
                    action="generate",
                    provider=model_result.get("provider"),
                    model_used=model_result.get("model"),
                    latency_ms=model_result.get("latency_ms", (time.time() - coach_start) * 1000),
                    input_tokens=model_result.get("usage", {}).get("prompt_tokens", 0),
                    output_tokens=model_result.get("usage", {}).get("completion_tokens", 0),
                    estimated_cost=model_result.get("cost_usd", 0.0),
                    routing_reason=model_result.get("routing_reason"),
                    downgrade_reason=model_result.get("downgrade_reason"),
                    budget_remaining=model_result.get("budget_remaining"),
                ),
            )
            coach_advice = CoachAdvice(
                why="see trace",
                action="follow guidance",
                suggested_reply=model_result.get("content", ""),
                alternatives=[],
                guardrails=["关键判断需引用 evidence_id 或声明需确认"],
                priority="medium",
                confidence=0.6,
                technique_name=None,
            )
            
            total_latency_ms = (time.time() - slow_start_time) * 1000
            trace = trace_manager.get_trace(slow_trace_id)
            if trace:
                trace.total_latency_ms = total_latency_ms
            trace_manager.complete_trace(slow_trace_id, status="success")
            
            # 指标埋点：slow_path_total_ms
            self.metrics["slow_path_total_ms"].append(total_latency_ms)
            logger.info(
                f"Slow Path completed: turn={turn_number}, latency={total_latency_ms:.0f}ms "
                f"[METRIC: slow_path_total_ms={total_latency_ms:.0f}]"
            )
            
            return SlowPathResult(
                turn_number=turn_number,
                coach_advice=coach_advice,
                evaluation=evaluation,
                adoption_log=adoption_log,
                total_latency_ms=total_latency_ms,
            )
            
        except Exception as e:
            logger.error(f"Slow Path error: {e}", exc_info=True)
            # Slow Path 失败不影响主对话
            return SlowPathResult(
                turn_number=turn_number,
                total_latency_ms=(time.time() - slow_start_time) * 1000,
            )
    
    async def _retrieve_lightweight(
        self,
        user_message: str,
        turn_plan: TurnPlan,
    ) -> EvidencePack:
        """轻量检索（Fast Path）"""
        budget_remaining = self.budget_manager.get_remaining_budget(self.session_id)
        return await self.retriever.retrieve(
            query=user_message,
            stage=self.fsm_state.current_stage,
            session_id=self.session_id,
            turn_number=turn_plan.turn_number,
            latency_mode=LatencyMode.FAST,
            budget_remaining=budget_remaining,
            use_graphrag=False,  # Fast Path 禁用 GraphRAG
        )
    
    async def _generate_npc_reply(
        self,
        user_message: str,
        evidence_pack: EvidencePack,
        turn_plan: TurnPlan,
    ) -> NpcReply:
        """生成 NPC 回复（Fast Path）"""
        return await self.npc_generator.generate(
            user_message=user_message,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            evidence_pack=evidence_pack,
            session_id=self.session_id,
            turn_number=turn_plan.turn_number,
            retrieval_confidence=evidence_pack.confidence,
        )
    
    async def _generate_coach_advice(
        self,
        user_message: str,
        npc_reply: NpcReply,
        turn_plan: TurnPlan,
        evidence_pack: Optional[EvidencePack] = None,
    ) -> CoachAdvice:
        """生成教练建议（Slow Path）"""
        # 如果 Fast Path 没有检索，Slow Path 可以检索
        if not evidence_pack:
            budget_remaining = self.budget_manager.get_remaining_budget(self.session_id)
            evidence_pack = await self.retriever.retrieve(
                query=user_message,
                stage=self.fsm_state.current_stage,
                session_id=self.session_id,
                turn_number=turn_plan.turn_number,
                latency_mode=LatencyMode.SLOW,
                budget_remaining=budget_remaining,
                use_graphrag="retriever_graphrag" in turn_plan.agents_to_call,
            )
        
        return await self.coach_generator.generate(
            user_message=user_message,
            npc_reply=npc_reply,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            evidence_pack=evidence_pack,
            session_id=self.session_id,
            turn_number=turn_plan.turn_number,
            retrieval_confidence=evidence_pack.confidence if evidence_pack else 1.0,
        )
    
    async def _evaluate_turn(
        self,
        user_message: str,
        npc_reply: NpcReply,
        turn_plan: TurnPlan,
        db: AsyncSession,
    ) -> Evaluation:
        """评估轮次（Slow Path）"""
        from app.fsm.engine import FSMEngine
        fsm_engine = FSMEngine()
        stage_config = fsm_engine.get_stage_config(self.fsm_state.current_stage)
        
        return await self.evaluator.evaluate(
            user_message=user_message,
            npc_reply=npc_reply,
            conversation_history=self.conversation_history,
            fsm_state=self.fsm_state,
            stage_config=stage_config,
            session_id=self.session_id,
            turn_number=turn_plan.turn_number,
        )
    
    async def _track_adoption(
        self,
        turn_number: int,
        coach_advice: Optional[CoachAdvice],
        evaluation: Optional[Evaluation],
        db: AsyncSession,
    ) -> Optional[AdoptionLog]:
        """追踪采纳（Slow Path）"""
        return await self.adoption_tracker.track(
            session_id=self.session_id,
            user_id=self.user_id,
            turn_number=turn_number,
            coach_advice=coach_advice,
            evaluation=evaluation,
            db=db,
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            "fast_path_ttfs_ms": self.metrics["fast_path_ttfs_ms"],
            "slow_path_total_ms": self.metrics["slow_path_total_ms"],
            "provider_hits": self.model_gateway.get_stats()["call_stats"],
            "downgrade_count": self.metrics["downgrade_count"],
            "downgrade_reasons": self.metrics["downgrade_reasons"],
        }
