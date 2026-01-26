"""
ReAct Reasoning Engine - 智能推理框架
实现 Thought → Action → Observation → Reflection 循环

替代原有的硬编码决策树，实现可追溯的智能推理

生产级 Prompt 模板:
- Thought: 深度 CoT 分析，6 步推理流程
- Action: 策略规划，混合 LLM + 启发式决策
- Observation: 效果观察与预测
- Reflection: 深度反思与经验提炼
"""
import json
import logging
import re
import time
from typing import Dict, Any, Optional, List, Literal
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.model_gateway import ModelGateway
from app.services.model_gateway.schemas import RoutingContext, LatencyMode, AgentType
from app.schemas.fsm import FSMState, SalesStage
from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ============================================================
# ReAct Schema Definitions
# ============================================================

class ReActPhase(str, Enum):
    """ReAct 推理阶段"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"


class ThoughtOutput(BaseModel):
    """Thought 阶段输出 - 分析当前情况"""
    situation_analysis: str = Field(..., description="当前销售情况分析")
    customer_signals: List[str] = Field(default_factory=list, description="识别的客户信号")
    key_challenges: List[str] = Field(default_factory=list, description="主要挑战")
    opportunities: List[str] = Field(default_factory=list, description="潜在机会")
    confidence: float = Field(..., ge=0.0, le=1.0, description="分析置信度")


class ActionOutput(BaseModel):
    """Action 阶段输出 - 规划行动"""
    action_type: Literal["respond", "escalate", "defer", "clarify"] = Field(...)
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    path_mode: Literal["fast", "slow", "both"] = Field(default="both")
    agents_to_call: List[str] = Field(default_factory=list)
    resource_allocation: Dict[str, float] = Field(default_factory=dict)
    rationale: str = Field(..., description="行动理由")


class ObservationOutput(BaseModel):
    """Observation 阶段输出 - 观察执行效果"""
    execution_success: bool = Field(...)
    customer_reaction: Optional[str] = Field(None, description="客户反应")
    outcome_signals: List[str] = Field(default_factory=list, description="结果信号")
    unexpected_events: List[str] = Field(default_factory=list, description="意外事件")
    metrics: Dict[str, float] = Field(default_factory=dict, description="关键指标")


class ReflectionOutput(BaseModel):
    """Reflection 阶段输出 - 反思与调整"""
    what_worked: List[str] = Field(default_factory=list, description="有效策略")
    what_failed: List[str] = Field(default_factory=list, description="失败策略")
    lessons_learned: List[str] = Field(default_factory=list, description="经验教训")
    adjustments: List[str] = Field(default_factory=list, description="调整建议")
    should_continue: bool = Field(default=False, description="是否需要继续推理")
    confidence_delta: float = Field(default=0.0, description="置信度变化")


class ReActStep(BaseModel):
    """单步 ReAct 推理"""
    step_number: int
    phase: ReActPhase
    thought: Optional[ThoughtOutput] = None
    action: Optional[ActionOutput] = None
    observation: Optional[ObservationOutput] = None
    reflection: Optional[ReflectionOutput] = None
    latency_ms: float = Field(default=0.0)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ReActResult(BaseModel):
    """ReAct 推理完整结果"""
    session_id: str
    turn_number: int
    steps: List[ReActStep] = Field(default_factory=list)
    final_decision: ActionOutput
    total_steps: int
    total_latency_ms: float
    final_confidence: float
    reasoning_trace: str = Field(..., description="完整推理链路")
    early_stopped: bool = Field(default=False, description="是否提前终止")
    stop_reason: Optional[str] = None


# ============================================================
# ReAct Configuration
# ============================================================

class ReActConfig(BaseModel):
    """ReAct 推理配置"""
    max_iterations: int = Field(default=3, ge=1, le=10, description="最大推理轮数")
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="置信度阈值")
    budget_per_step: float = Field(default=0.005, description="每步预算限制")
    enable_reflection: bool = Field(default=True, description="是否启用反思阶段")
    fast_path_confidence: float = Field(default=0.9, description="快路径置信度阈值")
    temperature: float = Field(default=0.3, description="推理温度")


# ============================================================
# ReAct Reasoning Engine
# ============================================================

class ReActReasoningEngine:
    """
    ReAct 推理引擎

    核心能力:
    - 实现 Thought → Action → Observation → Reflection 循环
    - 支持提前终止 (置信度达标/预算耗尽)
    - 完整推理链路追踪
    - 与现有 Agent 架构无缝集成
    """

    def __init__(
        self,
        model_gateway: ModelGateway,
        config: Optional[ReActConfig] = None,
    ):
        self.model_gateway = model_gateway
        self.config = config or ReActConfig()
        self.settings = get_settings()

        # 推理提示模板
        self._thought_prompt = self._build_thought_prompt()
        self._action_prompt = self._build_action_prompt()
        self._observation_prompt = self._build_observation_prompt()
        self._reflection_prompt = self._build_reflection_prompt()

    async def reason(
        self,
        turn_number: int,
        fsm_state: FSMState,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        session_id: str,
        user_id: str,
        budget_remaining: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReActResult:
        """
        执行 ReAct 推理循环

        Args:
            turn_number: 轮次号
            fsm_state: FSM 状态
            user_message: 用户消息
            conversation_history: 对话历史
            session_id: 会话ID
            user_id: 用户ID
            budget_remaining: 剩余预算
            context: 额外上下文

        Returns:
            ReActResult: 完整推理结果
        """
        start_time = time.time()
        steps: List[ReActStep] = []
        current_confidence = 0.5
        reasoning_traces: List[str] = []
        budget_consumed = 0.0

        logger.info(f"[ReAct] Starting reasoning for session={session_id}, turn={turn_number}")

        # 构建推理上下文
        reasoning_context = self._build_reasoning_context(
            fsm_state=fsm_state,
            user_message=user_message,
            conversation_history=conversation_history,
            context=context,
        )

        final_action: Optional[ActionOutput] = None
        early_stopped = False
        stop_reason = None

        for iteration in range(self.config.max_iterations):
            step_start = time.time()
            step_number = iteration + 1

            # 预算检查
            if budget_consumed + self.config.budget_per_step > budget_remaining:
                early_stopped = True
                stop_reason = "budget_exhausted"
                logger.warning(f"[ReAct] Budget exhausted at step {step_number}")
                break

            # Phase 1: Thought (思考)
            thought = await self._execute_thought(
                reasoning_context=reasoning_context,
                previous_steps=steps,
                session_id=session_id,
            )
            reasoning_traces.append(f"[Thought {step_number}] {thought.situation_analysis}")
            current_confidence = thought.confidence

            # Phase 2: Action (行动规划)
            action = await self._execute_action(
                thought=thought,
                fsm_state=fsm_state,
                reasoning_context=reasoning_context,
                session_id=session_id,
            )
            reasoning_traces.append(f"[Action {step_number}] {action.action_type}: {action.rationale}")
            final_action = action

            # Phase 3: Observation (观察 - 模拟执行效果)
            observation = await self._execute_observation(
                action=action,
                reasoning_context=reasoning_context,
            )
            reasoning_traces.append(f"[Observation {step_number}] Success={observation.execution_success}")

            # Phase 4: Reflection (反思)
            reflection = None
            if self.config.enable_reflection:
                reflection = await self._execute_reflection(
                    thought=thought,
                    action=action,
                    observation=observation,
                    previous_steps=steps,
                    session_id=session_id,
                )
                current_confidence += reflection.confidence_delta
                current_confidence = max(0.0, min(1.0, current_confidence))
                reasoning_traces.append(f"[Reflection {step_number}] Confidence={current_confidence:.2f}")

            # 记录步骤
            step_latency = (time.time() - step_start) * 1000
            step = ReActStep(
                step_number=step_number,
                phase=ReActPhase.REFLECTION if reflection else ReActPhase.OBSERVATION,
                thought=thought,
                action=action,
                observation=observation,
                reflection=reflection,
                latency_ms=step_latency,
            )
            steps.append(step)
            budget_consumed += self.config.budget_per_step

            # 终止条件检查
            if current_confidence >= self.config.confidence_threshold:
                early_stopped = True
                stop_reason = "confidence_reached"
                logger.info(f"[ReAct] Confidence threshold reached: {current_confidence:.2f}")
                break

            if reflection and not reflection.should_continue:
                early_stopped = True
                stop_reason = "reflection_complete"
                break

        # 构建最终结果
        total_latency = (time.time() - start_time) * 1000

        # 如果没有产生 action，使用默认
        if not final_action:
            final_action = ActionOutput(
                action_type="respond",
                path_mode="both",
                agents_to_call=["retriever", "npc_generator"],
                rationale="Default action due to reasoning failure",
            )

        result = ReActResult(
            session_id=session_id,
            turn_number=turn_number,
            steps=steps,
            final_decision=final_action,
            total_steps=len(steps),
            total_latency_ms=total_latency,
            final_confidence=current_confidence,
            reasoning_trace="\n".join(reasoning_traces),
            early_stopped=early_stopped,
            stop_reason=stop_reason,
        )

        logger.info(
            f"[ReAct] Completed: steps={len(steps)}, "
            f"confidence={current_confidence:.2f}, latency={total_latency:.0f}ms"
        )

        return result

    async def _execute_thought(
        self,
        reasoning_context: Dict[str, Any],
        previous_steps: List[ReActStep],
        session_id: str,
    ) -> ThoughtOutput:
        """执行 Thought 阶段 - 分析当前情况 (使用生产级 CoT 提示)"""

        # 构建历史思考链路
        previous_thoughts_list = []
        for i, s in enumerate(previous_steps):
            if s.thought:
                previous_thoughts_list.append(
                    f"Step {i+1}: {s.thought.situation_analysis} (置信度: {s.thought.confidence:.2f})"
                )
        previous_thoughts = "\n".join(previous_thoughts_list) if previous_thoughts_list else "这是首次分析，无历史推理"

        # 构建对话摘要
        history_length = reasoning_context.get('history_length', 0)
        if history_length > 0:
            conversation_summary = f"已进行 {history_length} 轮对话，当前处于第 {reasoning_context.get('turn_number', 0)} 轮"
        else:
            conversation_summary = "对话刚开始"

        # 使用生产级提示模板
        prompt = self._thought_prompt.format(
            stage=reasoning_context.get('stage', 'unknown'),
            user_message=reasoning_context.get('user_message', ''),
            turn_number=reasoning_context.get('turn_number', 0),
            mood=reasoning_context.get('mood', 'neutral'),
            slot_coverage=int(reasoning_context.get('slot_coverage', 0) * 20),  # 假设5个槽位
            conversation_summary=conversation_summary,
            previous_thoughts=previous_thoughts,
        )

        try:
            routing_context = RoutingContext(
                session_id=session_id,
                agent_type=AgentType.SESSION_DIRECTOR,
                latency_mode=LatencyMode.FAST,
                budget_authorized=True,
                budget_remaining=0.1,
            )

            response = await self.model_gateway.chat(
                agent_type=AgentType.SESSION_DIRECTOR,
                messages=[{"role": "user", "content": prompt}],
                context=routing_context,
                temperature=self.config.temperature,
                max_tokens=800,
            )

            # 解析响应
            content = response.get("content", "{}")
            data = self._parse_json_response(content)
            return ThoughtOutput(**data)

        except Exception as e:
            logger.error(f"[ReAct] Thought execution failed: {e}")
            return ThoughtOutput(
                situation_analysis=f"分析失败: {str(e)[:50]}",
                customer_signals=[],
                key_challenges=["推理过程出错"],
                opportunities=[],
                confidence=0.3,
            )

    async def _execute_action(
        self,
        thought: ThoughtOutput,
        fsm_state: FSMState,
        reasoning_context: Dict[str, Any],
        session_id: str,
    ) -> ActionOutput:
        """执行 Action 阶段 - 规划行动 (LLM + 启发式混合决策)"""

        # 构建思考分析摘要
        thought_analysis = f"""情况分析: {thought.situation_analysis}
客户信号: {', '.join(thought.customer_signals) if thought.customer_signals else '无明显信号'}
主要挑战: {', '.join(thought.key_challenges) if thought.key_challenges else '无明显挑战'}
潜在机会: {', '.join(thought.opportunities) if thought.opportunities else '无明显机会'}
置信度: {thought.confidence:.2f}"""

        stage = fsm_state.current_stage.value

        # 构建 Action 提示
        prompt = self._action_prompt.format(
            thought_analysis=thought_analysis,
            stage=stage,
        )

        try:
            routing_context = RoutingContext(
                session_id=session_id,
                agent_type=AgentType.SESSION_DIRECTOR,
                latency_mode=LatencyMode.FAST,
                budget_authorized=True,
                budget_remaining=0.1,
            )

            response = await self.model_gateway.chat(
                agent_type=AgentType.SESSION_DIRECTOR,
                messages=[{"role": "user", "content": prompt}],
                context=routing_context,
                temperature=self.config.temperature,
                max_tokens=600,
            )

            content = response.get("content", "{}")
            data = self._parse_json_response(content)

            # 验证并补充必要字段
            action_output = self._validate_action_output(data, thought, fsm_state)
            return action_output

        except Exception as e:
            logger.error(f"[ReAct] Action execution failed, fallback to heuristics: {e}")
            # 回退到启发式规则
            return self._fallback_action(thought, fsm_state, reasoning_context)

    def _validate_action_output(
        self,
        data: Dict[str, Any],
        thought: ThoughtOutput,
        fsm_state: FSMState,
    ) -> ActionOutput:
        """验证并补充 Action 输出"""

        # 确保必要的 agents
        agents = data.get("agents_to_call", [])
        if "retriever" not in agents:
            agents.insert(0, "retriever")
        if "npc_generator" not in agents:
            agents.append("npc_generator")

        # 确保资源分配
        resource_allocation = data.get("resource_allocation", {})
        for agent in agents:
            if agent not in resource_allocation:
                resource_allocation[agent] = 0.02

        # 验证优先级
        priority = data.get("priority", "medium")
        if priority not in ["high", "medium", "low"]:
            priority = "medium"

        # 验证路径模式
        path_mode = data.get("path_mode", "both")
        if path_mode not in ["fast", "slow", "both"]:
            path_mode = "both"

        # 验证行动类型
        action_type = data.get("action_type", "respond")
        if action_type not in ["respond", "clarify", "escalate", "defer"]:
            action_type = "respond"

        return ActionOutput(
            action_type=action_type,
            priority=priority,
            path_mode=path_mode,
            agents_to_call=agents,
            resource_allocation=resource_allocation,
            rationale=data.get("rationale", f"基于置信度 {thought.confidence:.2f} 的智能决策"),
        )

    def _fallback_action(
        self,
        thought: ThoughtOutput,
        fsm_state: FSMState,
        reasoning_context: Dict[str, Any],
    ) -> ActionOutput:
        """启发式回退策略"""

        # 1. 确定优先级
        if thought.confidence < 0.5:
            priority = "high"
        elif len(thought.key_challenges) > 2:
            priority = "high"
        else:
            priority = "medium"

        # 2. 确定路径模式
        stage = fsm_state.current_stage
        if stage in [SalesStage.CLOSING, SalesStage.OBJECTION_HANDLING]:
            path_mode = "both"
        elif thought.confidence > 0.8:
            path_mode = "fast"
        else:
            path_mode = "both"

        # 3. 确定调用的 Agent
        agents = ["retriever", "npc_generator"]
        if path_mode == "both":
            agents.extend(["coach_generator", "evaluator"])

        # 4. 确定行动类型
        user_msg = reasoning_context.get("user_message", "")
        if "投诉" in user_msg or "问题" in user_msg:
            action_type = "clarify"
        elif thought.confidence < 0.4:
            action_type = "defer"
        else:
            action_type = "respond"

        return ActionOutput(
            action_type=action_type,
            priority=priority,
            path_mode=path_mode,
            agents_to_call=agents,
            resource_allocation={agent: 0.02 for agent in agents},
            rationale=f"启发式决策 (置信度={thought.confidence:.2f})",
        )

    async def _execute_observation(
        self,
        action: ActionOutput,
        reasoning_context: Dict[str, Any],
        agent_results: Optional[Dict[str, Any]] = None,
        session_id: str = "",
    ) -> ObservationOutput:
        """
        执行 Observation 阶段 - 观察执行效果

        在实际场景中，这会观察 Agent 执行的结果。
        目前实现为模拟观察 + 预测分析。
        """

        # 构建行动摘要
        action_summary = f"""行动类型: {action.action_type}
优先级: {action.priority}
路径模式: {action.path_mode}
调用 Agent: {', '.join(action.agents_to_call)}
资源分配: {action.resource_allocation}
理由: {action.rationale}"""

        # Agent 结果摘要
        if agent_results:
            agent_results_summary = "\n".join([
                f"- {agent}: {result.get('status', 'unknown')}"
                for agent, result in agent_results.items()
            ])
        else:
            agent_results_summary = "Agent 尚未执行，基于规划进行预判"

        # 如果有真实的 agent_results，进行实际分析
        if agent_results:
            try:
                prompt = self._observation_prompt.format(
                    action_summary=action_summary,
                    agent_results=agent_results_summary,
                )

                routing_context = RoutingContext(
                    session_id=session_id,
                    agent_type=AgentType.SESSION_DIRECTOR,
                    latency_mode=LatencyMode.FAST,
                    budget_authorized=True,
                    budget_remaining=0.05,
                )

                response = await self.model_gateway.chat(
                    agent_type=AgentType.SESSION_DIRECTOR,
                    messages=[{"role": "user", "content": prompt}],
                    context=routing_context,
                    temperature=self.config.temperature,
                    max_tokens=400,
                )

                content = response.get("content", "{}")
                data = self._parse_json_response(content)

                return ObservationOutput(
                    execution_success=data.get("execution_success", True),
                    customer_reaction=data.get("customer_reaction"),
                    outcome_signals=data.get("outcome_signals", []),
                    unexpected_events=data.get("unexpected_events", []),
                    metrics=data.get("metrics", {}),
                )

            except Exception as e:
                logger.warning(f"[ReAct] Observation LLM failed, using defaults: {e}")

        # 默认/模拟观察
        return ObservationOutput(
            execution_success=True,
            customer_reaction=self._predict_customer_reaction(action, reasoning_context),
            outcome_signals=self._infer_outcome_signals(action),
            unexpected_events=[],
            metrics={
                "agents_called": len(action.agents_to_call),
                "budget_used": sum(action.resource_allocation.values()),
                "path_mode": 1.0 if action.path_mode == "fast" else 0.5,
            },
        )

    def _predict_customer_reaction(
        self,
        action: ActionOutput,
        reasoning_context: Dict[str, Any],
    ) -> str:
        """预测客户反应 (启发式)"""
        user_msg = reasoning_context.get("user_message", "").lower()
        stage = reasoning_context.get("stage", "")

        if action.action_type == "clarify":
            return "可能需要提供更多信息或澄清意图"
        elif action.action_type == "escalate":
            return "等待人工处理或高级支持"
        elif action.action_type == "defer":
            return "客户可能需要等待或重新表述"
        else:  # respond
            if "价格" in user_msg or "费用" in user_msg:
                return "关注价格信息，可能进入议价阶段"
            elif "权益" in user_msg or "功能" in user_msg:
                return "对产品细节感兴趣，可能在评估阶段"
            elif stage == "closing":
                return "接近决策点，需要把握促成时机"
            else:
                return "正常推进对话，观察后续反应"

    def _infer_outcome_signals(self, action: ActionOutput) -> List[str]:
        """推断结果信号 (启发式)"""
        signals = []

        if action.action_type == "respond":
            signals.append("正常响应客户问题")
        if "evaluator" in action.agents_to_call:
            signals.append("启用评估以分析表现")
        if "coach_generator" in action.agents_to_call:
            signals.append("提供销售指导建议")
        if action.priority == "high":
            signals.append("高优先级处理，增加资源投入")

        return signals

    async def _execute_reflection(
        self,
        thought: ThoughtOutput,
        action: ActionOutput,
        observation: ObservationOutput,
        previous_steps: List[ReActStep],
        session_id: str = "",
    ) -> ReflectionOutput:
        """执行 Reflection 阶段 - 深度反思 (LLM + 启发式混合)"""

        # 构建各阶段摘要
        thought_summary = f"""分析: {thought.situation_analysis}
信号: {thought.customer_signals}
挑战: {thought.key_challenges}
机会: {thought.opportunities}
置信度: {thought.confidence:.2f}"""

        action_summary = f"""行动类型: {action.action_type}
优先级: {action.priority}
路径模式: {action.path_mode}
调用 Agent: {action.agents_to_call}
理由: {action.rationale}"""

        observation_summary = f"""执行成功: {observation.execution_success}
客户反应: {observation.customer_reaction or '待观察'}
结果信号: {observation.outcome_signals}
意外事件: {observation.unexpected_events}
指标: {observation.metrics}"""

        # 构建历史步骤摘要
        previous_steps_list = []
        for i, s in enumerate(previous_steps):
            step_info = f"Step {i+1}: "
            if s.thought:
                step_info += f"分析='{s.thought.situation_analysis[:30]}...' "
            if s.action:
                step_info += f"行动={s.action.action_type} "
            if s.reflection:
                step_info += f"继续={s.reflection.should_continue}"
            previous_steps_list.append(step_info)
        previous_steps_summary = "\n".join(previous_steps_list) if previous_steps_list else "这是首轮推理"

        # 构建反思提示
        prompt = self._reflection_prompt.format(
            thought_summary=thought_summary,
            action_summary=action_summary,
            observation_summary=observation_summary,
            previous_steps_summary=previous_steps_summary,
        )

        try:
            routing_context = RoutingContext(
                session_id=session_id,
                agent_type=AgentType.SESSION_DIRECTOR,
                latency_mode=LatencyMode.FAST,
                budget_authorized=True,
                budget_remaining=0.1,
            )

            response = await self.model_gateway.chat(
                agent_type=AgentType.SESSION_DIRECTOR,
                messages=[{"role": "user", "content": prompt}],
                context=routing_context,
                temperature=self.config.temperature,
                max_tokens=600,
            )

            content = response.get("content", "{}")
            data = self._parse_json_response(content)

            # 验证并约束 confidence_delta
            confidence_delta = data.get("confidence_delta", 0.0)
            confidence_delta = max(-0.2, min(0.15, confidence_delta))

            return ReflectionOutput(
                what_worked=data.get("what_worked", []),
                what_failed=data.get("what_failed", []),
                lessons_learned=data.get("lessons_learned", []),
                adjustments=data.get("adjustments", []),
                should_continue=data.get("should_continue", False),
                confidence_delta=confidence_delta,
            )

        except Exception as e:
            logger.error(f"[ReAct] Reflection execution failed, fallback to heuristics: {e}")
            return self._fallback_reflection(thought, action, observation, previous_steps)

    def _fallback_reflection(
        self,
        thought: ThoughtOutput,
        action: ActionOutput,
        observation: ObservationOutput,
        previous_steps: List[ReActStep],
    ) -> ReflectionOutput:
        """启发式反思回退"""

        what_worked = []
        what_failed = []
        lessons = []
        adjustments = []

        if observation.execution_success:
            what_worked.append(f"{action.action_type} 策略执行成功")
            if thought.confidence > 0.7:
                lessons.append("高置信度分析配合正确行动类型效果良好")
        else:
            what_failed.append(f"{action.action_type} 策略执行失败")
            adjustments.append("考虑降级策略或增加信息收集")

        # 置信度调整
        confidence_delta = 0.0
        if observation.execution_success and thought.confidence > 0.7:
            confidence_delta = 0.1
        elif observation.execution_success:
            confidence_delta = 0.05
        elif not observation.execution_success:
            confidence_delta = -0.15

        # 是否需要继续推理
        should_continue = (
            thought.confidence < 0.8
            and len(previous_steps) < 2
            and not observation.execution_success
        )

        return ReflectionOutput(
            what_worked=what_worked,
            what_failed=what_failed,
            lessons_learned=lessons,
            adjustments=adjustments,
            should_continue=should_continue,
            confidence_delta=confidence_delta,
        )

    def _build_reasoning_context(
        self,
        fsm_state: FSMState,
        user_message: str,
        conversation_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构建推理上下文"""
        return {
            "stage": fsm_state.current_stage.value,
            "turn_number": fsm_state.turn_count,
            "user_message": user_message,
            "mood": fsm_state.npc_mood,
            "slot_coverage": len([v for v in fsm_state.slot_values.values() if v.value]),
            "history_length": len(conversation_history),
            "extra": context or {},
        }

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析 LLM 响应中的 JSON"""
        # 尝试提取 JSON 代码块
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]

        # 清理常见问题
        content = content.strip()

        # 尝试解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复常见的 JSON 格式问题
            # 1. 处理单引号
            content = content.replace("'", '"')
            # 2. 处理尾部逗号
            content = re.sub(r',\s*}', '}', content)
            content = re.sub(r',\s*]', ']', content)

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"[ReAct] JSON parse failed: {e}, content: {content[:200]}")
                return {}

    def _build_thought_prompt(self) -> str:
        """构建 Thought 提示模板 - 深度 CoT 分析"""
        return """你是一个专业的销售培训 AI 推理引擎。请对当前销售情况进行深度分析。

## 角色定位
你是一个经验丰富的销售教练，正在实时分析学员与模拟客户的对话。你的任务是识别关键信号、评估形势、发现机会与挑战。

## 当前销售情境
- **销售阶段**: {stage}
- **客户最新消息**: {user_message}
- **对话轮次**: 第 {turn_number} 轮
- **NPC 情绪状态**: {mood}
- **已收集信息覆盖率**: {slot_coverage}%

## 对话历史摘要
{conversation_summary}

## 历史推理链路
{previous_thoughts}

## 分析任务 (Chain of Thought)

请按照以下步骤逐层分析，展现你的推理过程：

### Step 1: 信息解读
- 客户这句话的字面含义是什么？
- 背后可能隐藏的真实意图是什么？
- 客户的情绪是积极、中立还是消极？

### Step 2: 信号识别
识别以下类型的信号（如有）：
- 🟢 **购买信号**: 询问价格、功能细节、办理流程
- 🟡 **犹豫信号**: 需要考虑、比较其他产品、时间不确定
- 🔴 **拒绝信号**: 明确拒绝、不需要、负面评价
- 🔵 **信息需求**: 询问具体功能、权益、费用

### Step 3: 阶段匹配
- 当前销售阶段是否适合处理这个信号？
- 是否需要回退或跳跃到其他阶段？
- 阶段转换的条件是否满足？

### Step 4: 挑战评估
识别当前面临的主要挑战：
- 客户异议：具体是什么异议？
- 信息缺口：还缺少什么关键信息？
- 节奏问题：是否推进太快或太慢？

### Step 5: 机会发现
识别可利用的机会：
- 客户展现的兴趣点
- 可以深挖的话题
- 建立信任的契机

### Step 6: 置信度评估
综合以上分析，评估你对这个分析的置信度 (0-1)：
- 0.0-0.3: 信息不足，难以判断
- 0.4-0.6: 有一定把握，但存在不确定性
- 0.7-0.8: 较有信心，分析较为可靠
- 0.9-1.0: 非常确定，信号明确

## 输出格式

请用 JSON 格式输出你的分析结果：
```json
{{
    "situation_analysis": "一句话总结当前销售形势",
    "customer_signals": [
        "信号1: 具体描述",
        "信号2: 具体描述"
    ],
    "key_challenges": [
        "挑战1: 具体描述",
        "挑战2: 具体描述"
    ],
    "opportunities": [
        "机会1: 具体描述",
        "机会2: 具体描述"
    ],
    "confidence": 0.xx
}}
```

注意：
- situation_analysis 应该简洁有力，不超过50字
- customer_signals 要具体，说明是什么类型的信号
- key_challenges 和 opportunities 各列出1-3个最重要的
- confidence 要基于分析过程实事求是地给出"""

    def _build_action_prompt(self) -> str:
        """构建 Action 提示模板 - 策略规划"""
        return """你是一个销售培训系统的策略规划器。基于前序的思考分析，规划最优的响应行动。

## 角色定位
你需要决定：
1. 采取什么类型的行动
2. 调用哪些 AI Agent
3. 分配多少资源
4. 选择什么响应路径

## 思考阶段的分析结果
{thought_analysis}

## 当前销售阶段
{stage}

## 可用的 Agent 列表
| Agent | 职责 | 适用场景 | 资源消耗 |
|-------|------|----------|----------|
| retriever | 知识检索 | 需要产品/权益信息时 | 低 |
| npc_generator | NPC回复生成 | 每轮必需 | 中 |
| coach_generator | 销售建议生成 | 需要指导时 | 中 |
| evaluator | 表现评估 | 关键节点评估 | 高 |
| compliance_check | 合规检查 | 涉及敏感话题时 | 低 |

## 响应路径说明
- **fast**: 快速响应，仅用核心 Agent，适合简单轮次
- **slow**: 完整响应，调用全部相关 Agent，适合复杂情况
- **both**: 双路径并行，先快后慢，平衡速度与质量

## 行动类型说明
- **respond**: 正常响应客户
- **clarify**: 澄清客户意图，需要更多信息
- **escalate**: 升级处理，遇到无法处理的情况
- **defer**: 延迟响应，需要更多思考

## 决策 Chain of Thought

### Step 1: 评估紧迫性
- 客户是否在等待直接回答？
- 是否有时间进行深度分析？
- 当前阶段的重要程度如何？

### Step 2: 选择行动类型
基于思考分析中的置信度和信号：
- 置信度 > 0.8 且信号明确 → respond
- 置信度 0.5-0.8 且有疑问 → clarify
- 置信度 < 0.5 或情况复杂 → defer
- 遇到红线问题 → escalate

### Step 3: 规划 Agent 调用
根据当前需求选择 Agent：
- 每轮必须调用: retriever, npc_generator
- 关键阶段追加: coach_generator, evaluator
- 敏感话题追加: compliance_check

### Step 4: 选择响应路径
- 简单问候/确认 → fast
- 产品咨询/异议处理 → both
- 复杂谈判/促成成交 → slow

### Step 5: 资源分配
总预算不超过 0.1，按重要性分配：
- npc_generator: 必须预留 0.02-0.04
- retriever: 0.01-0.02
- 其他 Agent: 0.01-0.02

## 输出格式

请用 JSON 格式输出行动规划：
```json
{{
    "action_type": "respond|clarify|escalate|defer",
    "priority": "high|medium|low",
    "path_mode": "fast|slow|both",
    "agents_to_call": ["agent1", "agent2"],
    "resource_allocation": {{
        "agent1": 0.02,
        "agent2": 0.03
    }},
    "rationale": "简要说明选择这个行动的理由"
}}
```"""

    def _build_observation_prompt(self) -> str:
        """构建 Observation 提示模板 - 效果观察"""
        return """你是销售培训系统的效果观察器。分析行动执行后的效果。

## 角色定位
在实际运行中，你会观察到各个 Agent 的执行结果。现在请基于可用信息进行预判和分析。

## 执行的行动
{action_summary}

## 调用的 Agent 及结果
{agent_results}

## 观察维度

### 1. 执行成功性
- 所有 Agent 是否正常返回？
- 返回结果是否符合预期？
- 是否有超时或错误？

### 2. 客户反应预测
基于 NPC 特性和当前情境，预测客户可能的反应：
- 积极反应：表示认同、继续追问、展现兴趣
- 中性反应：不置可否、转换话题
- 消极反应：表示不满、提出新异议、拒绝

### 3. 结果信号识别
从执行结果中识别重要信号：
- 是否成功回答了客户问题？
- 是否推进了销售进程？
- 是否建立了更多信任？

### 4. 意外事件检测
检测是否有意外情况：
- 检索到的信息与问题不匹配
- 生成的回复可能引起误解
- 合规风险

## 输出格式

```json
{{
    "execution_success": true|false,
    "customer_reaction": "预测的客户反应描述",
    "outcome_signals": [
        "结果信号1",
        "结果信号2"
    ],
    "unexpected_events": [
        "意外事件1 (如有)"
    ],
    "metrics": {{
        "relevance_score": 0.xx,
        "progress_score": 0.xx,
        "risk_score": 0.xx
    }}
}}
```"""

    def _build_reflection_prompt(self) -> str:
        """构建 Reflection 提示模板 - 深度反思"""
        return """你是销售培训系统的反思引擎。对本轮推理过程进行深度复盘。

## 角色定位
作为元认知层，你需要审视整个推理过程，识别改进空间，提炼经验教训。

## 本轮推理过程

### Thought (思考阶段)
{thought_summary}

### Action (行动阶段)
{action_summary}

### Observation (观察阶段)
{observation_summary}

## 历史推理步骤
{previous_steps_summary}

## 反思维度

### 1. 有效性分析
回顾本轮推理，哪些判断和决策是有效的：
- 情况分析是否准确？
- 信号识别是否完整？
- 行动选择是否恰当？

### 2. 失误分析
识别本轮推理中的不足：
- 是否遗漏了重要信号？
- 行动规划是否可以更优？
- 资源分配是否合理？

### 3. 经验提炼
从本轮推理中提炼可复用的经验：
- 对于这类情况，什么策略更有效？
- 如何避免类似的失误？
- 有什么通用的规律？

### 4. 策略调整
基于反思，建议的调整方向：
- 是否需要调整信号权重？
- 是否需要改变行动策略？
- 下一轮推理应该注意什么？

### 5. 置信度调整
基于执行效果，调整推理置信度：
- 执行成功 + 分析准确 → +0.1 到 +0.15
- 执行成功 + 分析有偏差 → +0.05
- 执行失败 + 可解释 → -0.05 到 -0.1
- 执行失败 + 难以解释 → -0.15 到 -0.2

### 6. 终止判断
评估是否需要继续推理：
- 置信度已达标 (>0.85) → 可以终止
- 情况已明确，行动方案确定 → 可以终止
- 仍有不确定性，需要更多分析 → 继续推理
- 已达最大步数 → 强制终止

## 输出格式

```json
{{
    "what_worked": [
        "有效策略1: 具体描述",
        "有效策略2: 具体描述"
    ],
    "what_failed": [
        "失误1: 具体描述 (如有)"
    ],
    "lessons_learned": [
        "经验1: 可复用的规律",
        "经验2: 避免的陷阱"
    ],
    "adjustments": [
        "调整建议1: 下一步应该...",
        "调整建议2: 注意..."
    ],
    "should_continue": true|false,
    "confidence_delta": 0.xx
}}
```

注意：
- confidence_delta 范围在 -0.2 到 +0.15 之间
- should_continue 要基于终止条件综合判断
- lessons_learned 要有实际参考价值"""


# ============================================================
# Utility Functions
# ============================================================

def convert_react_to_turn_plan(react_result: ReActResult) -> Dict[str, Any]:
    """将 ReAct 结果转换为 TurnPlan 格式 (向后兼容)"""
    action = react_result.final_decision

    return {
        "turn_number": react_result.turn_number,
        "path_mode": action.path_mode,
        "agents_to_call": action.agents_to_call,
        "budget_allocation": action.resource_allocation,
        "model_upgrade": action.priority == "high",
        "risk_level": "high" if action.priority == "high" else "low",
        "evidence_confidence": react_result.final_confidence,
        "reasoning": react_result.reasoning_trace[:500],  # 截断
    }
