"""
Dynamic Workflow Builder
Constructs LangGraph execution graphs based on runtime configuration
"""
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field, model_validator
try:
    from pydantic import ConfigDict
except ImportError:  # pydantic < 2 fallback
    ConfigDict = None  # type: ignore
from enum import Enum

from langgraph.graph import StateGraph, END

from ...engine.coordinator.state import CoordinatorState
from ...engine.coordinator.bandit import SimpleContextualBandit
from ...engine.coordinator.bandit_redis import RedisContextualBandit
from ...engine.coordinator.routing_fallback import fallback_route
from ...engine.coordinator.schemas import BanditContextSchema
from ...engine.coordinator.reasoning_engine import ReasoningEngine
from ...engine.coordinator.routing_policy import RoutingAdvisor
from ...engine.coordinator.trace_utils import build_trace_event
from ...infra.gateway.schemas import AgentType
from ...core.config import get_settings
from ...observability.otel_tracing import node_span

logger = logging.getLogger(__name__)


# ==================== Fallback Coach Advice (Graceful Degradation) ====================

FALLBACK_COACH_ADVICE = {
    # Intent-based fallback advice
    "price_inquiry": {
        "advice": "客户询问价格时，建议先强调产品价值，避免直接报价。可以说：'让我先了解一下您的具体需求，这样我能为您推荐最合适的方案。'",
        "tips": [
            "不要急于报价，先建立价值感",
            "询问预算范围，了解客户期望",
            "准备好价格锚定策略"
        ]
    },
    "objection_price": {
        "advice": "面对价格异议时，要转移焦点到投资回报率（ROI）。可以说：'我理解价格是重要考虑因素，但更重要的是这个投资能为您带来什么价值。'",
        "tips": [
            "不要直接降价，先挖掘真实异议",
            "强调产品价值和长期收益",
            "提供成功案例证明ROI"
        ]
    },
    "objection_competitor": {
        "advice": "客户提到竞品时，不要贬低对手，而要突出自身差异化优势。可以说：'XX产品确实不错，我们的独特之处在于...'",
        "tips": [
            "尊重竞品，展现专业态度",
            "突出自身独特价值主张",
            "询问客户最看重的因素"
        ]
    },
    "closing_signal": {
        "advice": "客户出现成交信号时，要及时推进。可以问：'您觉得这个方案符合您的需求吗？我们什么时候可以开始？'",
        "tips": [
            "识别成交信号（点头、询问细节、关注价格）",
            "使用假设成交法推进",
            "准备好合同和下一步流程"
        ]
    },
    "product_inquiry": {
        "advice": "客户询问产品细节时，要将功能转化为客户利益。不要只说'我们有XX功能'，而要说'这个功能能帮您...'",
        "tips": [
            "使用FAB法则（Feature-Advantage-Benefit）",
            "结合客户场景讲解",
            "准备演示或案例"
        ]
    },
    "greeting": {
        "advice": "开场很关键，要快速建立信任。使用开放式问题了解客户需求，避免直接推销。",
        "tips": [
            "微笑、眼神交流、专业着装",
            "用开放式问题引导对话",
            "倾听并记录关键信息"
        ]
    },
    "benefit_inquiry": {
        "advice": "客户询问收益时，要用具体数字和案例说话。可以说：'我们的客户平均在3个月内看到XX%的效率提升。'",
        "tips": [
            "准备量化的ROI数据",
            "分享相似客户的成功案例",
            "提供试用或演示机会"
        ]
    },
    # Default fallback
    "default": {
        "advice": "保持积极倾听，理解客户真实需求。用开放式问题引导对话，展现专业和同理心。",
        "tips": [
            "多问少说，80/20原则",
            "记录客户关键信息",
            "确认理解后再回应"
        ]
    },
    # Error fallback (when AI fails completely)
    "error_fallback": {
        "advice": "建议回顾对话要点，确认客户需求是否已充分了解。必要时可以说：'让我总结一下您的需求，看我理解得对不对。'",
        "tips": [
            "保持冷静和专业",
            "使用澄清性问题确认理解",
            "展现解决问题的意愿"
        ]
    }
}


class NodeType(str, Enum):
    """可用的节点类型"""
    INTENT = "intent"
    KNOWLEDGE = "knowledge"
    NPC = "npc"
    COACH = "coach"
    COMPLIANCE = "compliance"
    TOOLS = "tools"
    CUSTOM = "custom"


class WorkflowConfig(BaseModel):
    """工作流配置"""

    # 启用的节点
    enabled_nodes: Set[NodeType] = Field(
        default={NodeType.INTENT, NodeType.NPC},
        description="启用的节点列表"
    )

    # 节点参数
    node_params: Dict[NodeType, Dict[str, Any]] = Field(
        default_factory=dict,
        description="每个节点的参数配置"
    )

    # 路由规则
    routing_rules: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="自定义路由规则: {from_node: [to_nodes]}"
    )

    # 并行执行节点
    parallel_nodes: List[Set[NodeType]] = Field(
        default_factory=list,
        description="可并行执行的节点组"
    )

    # 条件路由配置
    conditional_routing: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="条件路由配置: {from_node: {condition: to_node}}"
    )

    # Routing aliases (policy -> graph)
    routing_aliases: Dict[str, str] = Field(
        default_factory=lambda: {"tools": "knowledge"},
        description="Map policy node names to graph node names"
    )

    # Reasoning & routing policy
    enable_reasoning: bool = Field(
        default=True,
        description="Enable reasoning node for structured analysis"
    )
    enable_routing_policy: bool = Field(
        default=True,
        description="Enable routing policy advisor"
    )
    routing_min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence required to accept routing policy output"
    )

    # Bandit routing (optional)
    enable_bandit: bool = Field(
        default=False,
        description="Enable contextual bandit for routing decisions"
    )
    bandit_exploration_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Exploration rate for contextual bandit"
    )

    # 元数据
    name: str = Field(default="default_workflow", description="工作流名称")
    version: str = Field(default="1.0", description="工作流版本")
    description: str = Field(default="", description="工作流描述")

    if ConfigDict is not None:
        model_config = ConfigDict(use_enum_values=True)
    else:
        class Config:
            use_enum_values = True

    @model_validator(mode='after')
    def validate_dag(self):
        """
        Validate that the workflow configuration forms a valid DAG (Directed Acyclic Graph)

        Checks:
        1. No cycles in routing
        2. All referenced nodes are enabled
        3. At least one path to END
        """
        from collections import deque

        # Build adjacency list
        graph = {}
        enabled_node_names = {
            n.value if hasattr(n, "value") else str(n)
            for n in self.enabled_nodes
        }

        # Add routing rules
        for from_node, to_nodes in self.routing_rules.items():
            if from_node not in graph:
                graph[from_node] = []
            graph[from_node].extend(to_nodes)

        # Add conditional routing
        for from_node, conditions in self.conditional_routing.items():
            if from_node not in graph:
                graph[from_node] = []
            graph[from_node].extend(conditions.values())

        # Check 1: All referenced nodes must be enabled
        all_nodes = set(graph.keys())
        for to_nodes in graph.values():
            all_nodes.update(to_nodes)

        # Remove special nodes
        all_nodes.discard("END")
        all_nodes.discard("end")

        invalid_nodes = all_nodes - enabled_node_names
        if invalid_nodes:
            raise ValueError(
                f"Routing references disabled nodes: {invalid_nodes}. "
                f"Enabled nodes: {enabled_node_names}"
            )

        # Check 2: Detect cycles using DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor in ("END", "end"):
                    continue

                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for node in graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    raise ValueError(
                        f"Workflow configuration contains a cycle. "
                        f"DAG validation failed. Graph: {graph}"
                    )

        # Check 3: Verify at least one path to END
        # Find entry point
        entry_point = None
        if NodeType.INTENT in self.enabled_nodes:
            entry_point = NodeType.INTENT.value
        elif self.enabled_nodes:
            entry_point = list(self.enabled_nodes)[0]
            if hasattr(entry_point, "value"):
                entry_point = entry_point.value

        if entry_point:
            # BFS to check if END is reachable
            queue = deque([entry_point])
            visited_bfs = {entry_point}
            found_end = False

            while queue:
                current = queue.popleft()

                neighbors = graph.get(current, [])
                for neighbor in neighbors:
                    if neighbor in ("END", "end"):
                        found_end = True
                        break

                    if neighbor not in visited_bfs:
                        visited_bfs.add(neighbor)
                        queue.append(neighbor)

                if found_end:
                    break

            if not found_end:
                logger.warning(
                    f"[WorkflowConfig] No path to END found from entry point '{entry_point}'. "
                    f"This may cause the workflow to hang."
                )

        return self


class DynamicWorkflowCoordinator:
    """
    动态工作流编排器

    根据配置文件动态构建LangGraph执行图

    Example:
        config = WorkflowConfig(
            enabled_nodes={NodeType.INTENT, NodeType.KNOWLEDGE, NodeType.NPC},
            routing_rules={
                "intent": ["knowledge"],
                "knowledge": ["npc"]
            }
        )

        coordinator = DynamicWorkflowCoordinator(dependencies, config)
        result = await coordinator.execute_turn(...)
    """

    def __init__(
        self,
        model_gateway,
        budget_manager,
        persona,
        config: WorkflowConfig
    ):
        self.model_gateway = model_gateway
        self.budget_manager = budget_manager
        self.persona = persona
        self.config = config

        # Per-session AgentMemory instances (keyed by session_id).
        # Populated lazily on first execute_turn call for a session.
        # Call close_session(session_id) to flush and release.
        self._session_memories: Dict[str, Any] = {}

        # 初始化节点实现
        self._init_node_implementations()

        # 动态构建图
        self.graph = self._build_dynamic_graph()
        self.app = self._compile_with_checkpointer()

        logger.info(
            f"[DynamicWorkflow] Built workflow '{config.name}' "
            f"with nodes: {config.enabled_nodes}"
        )

    def _compile_with_checkpointer(self):
        """Compile graph with Redis checkpointer for cross-worker state persistence.
        Falls back to MemorySaver when Redis is unavailable."""
        try:
            from langgraph.checkpoint.redis import AsyncRedisSaver
            settings = get_settings()
            redis_url = getattr(settings, 'REDIS_URL', None)
            if not redis_url:
                raise ValueError("REDIS_URL not configured")
            checkpointer = AsyncRedisSaver.from_conn_string(redis_url)
            logger.info("[DynamicWorkflow] Using Redis checkpointer: %s", redis_url)
            return self.graph.compile(checkpointer=checkpointer)
        except Exception as e:
            from langgraph.checkpoint.memory import MemorySaver
            logger.warning(
                "[DynamicWorkflow] Redis checkpointer unavailable (%s), "
                "falling back to MemorySaver — workflow state is PROCESS-LOCAL only.",
                e,
            )
            return self.graph.compile(checkpointer=MemorySaver())

    def _init_node_implementations(self):
        """初始化所有可用的节点实现"""
        # 导入节点实现（避免循环导入）
        from ...engine.intent.context_aware_classifier import (
            ContextAwareIntentClassifier
        )
        from ...agents.practice.npc_simulator import NPCGenerator
        from ...agents.ask.coach_agent import SalesCoachAgent
        from ...tools.registry import build_default_registry
        from ...tools.executor import ToolExecutor

        self.intent_classifier = ContextAwareIntentClassifier()
        self.npc_agent = NPCGenerator(model_gateway=self.model_gateway)
        self.coach_agent = SalesCoachAgent()
        self.tool_registry = build_default_registry()
        self.tool_executor = ToolExecutor(self.tool_registry)

        self.reasoning_engine = ReasoningEngine(self.model_gateway, self.tool_registry)
        self.routing_advisor = RoutingAdvisor(self.model_gateway, self.tool_registry)
        self.bandit = None
        if self.config.enable_bandit:
            settings = get_settings()
            if settings.BANDIT_REDIS_ENABLED:
                try:
                    self.bandit = RedisContextualBandit(
                        settings.REDIS_URL,
                        epsilon=self.config.bandit_exploration_rate,
                    )
                except Exception:
                    self.bandit = SimpleContextualBandit(self.config.bandit_exploration_rate)
            else:
                self.bandit = SimpleContextualBandit(self.config.bandit_exploration_rate)
        if not self.config.enable_reasoning:
            self.reasoning_engine = None
        if not self.config.enable_routing_policy:
            self.routing_advisor = None
        if not self.config.enable_bandit:
            self.bandit = None

    def _make_tool_call_id(self, tool_name: str, state: CoordinatorState) -> str:
        session_id = state.get("session_id", "unknown")
        turn_number = state.get("turn_number", 0)
        suffix = uuid.uuid4().hex[:8]
        return f"{session_id}-{turn_number}-{tool_name}-{suffix}"

    def _get_intent_candidates(self) -> List[str]:
        candidates: List[str] = []
        conditions = self.config.conditional_routing.get("intent") or {}
        if conditions:
            candidates = list(conditions.values())
        if not candidates:
            candidates = list(self.config.routing_rules.get("intent", []))
        if not candidates:
            enabled = {n.value if hasattr(n, "value") else str(n) for n in self.config.enabled_nodes}
            if "knowledge" in enabled:
                candidates.append("knowledge")
            if "tools" in enabled:
                candidates.append("tools")
            if "npc" in enabled:
                candidates.append("npc")
        # de-duplicate while preserving order
        seen = set()
        ordered: List[str] = []
        for item in candidates:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _policy_candidates(self, graph_candidates: List[str]) -> List[str]:
        aliases = self.config.routing_aliases or {}
        inverse = {v: k for k, v in aliases.items()}
        mapped = [inverse.get(c, c) for c in graph_candidates]
        seen = set()
        ordered: List[str] = []
        for item in mapped:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _map_policy_target(self, target: str, graph_candidates: List[str]) -> str:
        aliases = self.config.routing_aliases or {}
        mapped = aliases.get(target, target)
        if mapped in graph_candidates:
            return mapped
        return target

    def _build_dynamic_graph(self) -> StateGraph:
        """根据配置动态构建图"""
        workflow = StateGraph(CoordinatorState)

        # 1. add enabled nodes
        enabled_names = {n.value if hasattr(n, 'value') else str(n) for n in self.config.enabled_nodes}
        for node_type in self.config.enabled_nodes:
            node_name = node_type.value if hasattr(node_type, 'value') else str(node_type)
            node_func = self._get_node_function(node_name)
            workflow.add_node(node_name, node_func)

        # 2. set entry point
        if NodeType.INTENT.value in enabled_names:
            workflow.set_entry_point(NodeType.INTENT.value)
        else:
            # use first enabled node as entry
            first_node = next(iter(enabled_names), None)
            if not first_node:
                raise ValueError('No enabled nodes configured for workflow')
            workflow.set_entry_point(first_node)

        # 3. 添加路由边
        self._add_routing_edges(workflow)

        return workflow

    def _get_node_function(self, node_type: str):
        """获取节点对应的执行函数"""
        node_map = {
            NodeType.INTENT.value: self._intent_node,
            NodeType.KNOWLEDGE.value: self._knowledge_node,
            NodeType.NPC.value: self._npc_node,
            NodeType.COACH.value: self._coach_node,
            NodeType.COMPLIANCE.value: self._compliance_node,
            NodeType.TOOLS.value: self._tools_node,
        }

        func = node_map.get(node_type)
        if not func:
            # Fallback for Enum vs String mismatch if any
            # Try looking up by enum if string passed
            try:
                enum_val = NodeType(node_type)
                func = node_map.get(enum_val.value)
            except:
                pass
                
        if not func:
            raise ValueError(f"Unknown node type: {node_type}")

        return func

    def _add_routing_edges(self, workflow: StateGraph):
        """添加路由边"""
        # 1. 简单路由（固定连接）
        for from_node, to_nodes in self.config.routing_rules.items():
            if len(to_nodes) == 1:
                # 单一路径 -> 直接边
                workflow.add_edge(from_node, to_nodes[0])
            else:
                # 多路径 -> 条件路由（需要路由函数）
                logger.warning(
                    f"[DynamicWorkflow] Multiple targets for {from_node}, "
                    f"using conditional routing"
                )

        # 2. 条件路由
        for from_node, conditions in self.config.conditional_routing.items():
            router_func = self._create_router_function(from_node, conditions)
            workflow.add_conditional_edges(from_node, router_func, conditions)

        # 3. 自动推断终止节点
        # 如果启用了compliance，连接到END
        enabled_names = {n.value if hasattr(n, 'value') else str(n) for n in self.config.enabled_nodes}
        if NodeType.COMPLIANCE.value in enabled_names:
            workflow.add_edge(NodeType.COMPLIANCE.value, END)
        elif NodeType.NPC.value in enabled_names:
            workflow.add_edge(NodeType.NPC.value, END)

    def _create_router_function(self, from_node: str, conditions: Dict[str, str]):
        """动态创建路由函数"""

        def router(state: CoordinatorState) -> str:
            """根据状态决定下一个节点"""
            # 默认路由逻辑（可根据需求扩展）
            state.get("intent", "")

            if from_node == "intent":
                route_choice = state.get("route_choice")
                if route_choice in conditions.values():
                    return route_choice
                fallback = fallback_route(state, list(conditions.values()))
                return fallback["target_node"]

            # Other nodes use the first configured target
            return list(conditions.values())[0]

        return router

    # ==================== 节点实现 ====================

    async def _intent_node(self, state: CoordinatorState) -> Dict:
        """?????????"""
        result = await self.intent_classifier.classify_with_context(
            message=state["user_message"],
            history=state.get("history", []),
            fsm_state=state.get("fsm_state", {})
        )

        intent = result.intent
        confidence = result.confidence
        stage_suggestion = result.stage_suggestion or ""
        recent_tool_calls = bool(state.get("recent_tool_calls", False))

        analysis_state = dict(state)
        analysis_state.update({
            "intent": intent,
            "confidence": confidence,
            "stage_suggestion": stage_suggestion,
            "recent_tool_calls": recent_tool_calls,
        })

        reasoning = None
        reasoning_source = "disabled"
        if self.reasoning_engine:
            reasoning, reasoning_source = await self.reasoning_engine.analyze(analysis_state)
        analysis_state["reasoning"] = reasoning or {}

        graph_candidates = self._get_intent_candidates()
        policy_candidates = self._policy_candidates(graph_candidates)
        routing_recommendation = None
        routing_source = "disabled"
        if self.routing_advisor and policy_candidates:
            routing_recommendation, routing_source = await self.routing_advisor.advise(
                analysis_state, reasoning or {}, policy_candidates
            )

        routing_decision = None
        bandit_decision = None
        route_choice = None

        if routing_recommendation:
            policy_target = routing_recommendation.get("target_node")
            mapped_target = self._map_policy_target(policy_target, graph_candidates)
            if mapped_target in graph_candidates and routing_recommendation.get("confidence", 0.0) >= self.config.routing_min_confidence:
                routing_decision = {
                    "target_node": mapped_target,
                    "confidence": routing_recommendation.get("confidence", 0.0),
                    "reason": routing_recommendation.get("reason", "policy routing"),
                    "source": "policy",
                }
                route_choice = mapped_target

        if not route_choice and self.bandit and graph_candidates:
            risk_flags = []
            if reasoning and reasoning.get("risk", {}).get("compliance_risk"):
                risk_flags.append("compliance")
            if reasoning and reasoning.get("risk", {}).get("need_human"):
                risk_flags.append("human")
            context = {
                "intent": intent,
                "confidence": float(confidence or 0.0),
                "fsm_stage": state.get("fsm_state", {}).get("current_stage", ""),
                "need_tools": bool(reasoning.get("need_tools")) if reasoning else False,
                "risk_flags": risk_flags,
                "recent_tool_calls": recent_tool_calls,
            }
            try:
                BanditContextSchema.model_validate(context)
                bandit_decision = self.bandit.choose(context, graph_candidates)
                bandit_target = self._map_policy_target(bandit_decision["chosen"], graph_candidates)
                if bandit_target in graph_candidates:
                    routing_decision = {
                        "target_node": bandit_target,
                        "confidence": bandit_decision.get("score", 0.0),
                        "reason": "bandit routing",
                        "source": "bandit",
                        "decision_id": bandit_decision.get("decision_id"),
                    }
                    route_choice = bandit_target
            except Exception:
                bandit_decision = None

        if not route_choice:
            fallback_decision = fallback_route(analysis_state, graph_candidates)
            routing_decision = fallback_decision
            route_choice = fallback_decision.get("target_node")

        trace_entry = build_trace_event(
            node="intent",
            source=routing_decision.get("source") if routing_decision else routing_source,
            detail={
                "intent": intent,
                "route_choice": route_choice,
                "reasoning_source": reasoning_source,
                "routing_source": routing_source,
                "policy_confidence": routing_recommendation.get("confidence") if routing_recommendation else None,
                "bandit_decision_id": bandit_decision.get("decision_id") if bandit_decision else None,
            },
        )

        return {
            "intent": intent,
            "confidence": confidence,
            "stage_suggestion": stage_suggestion,
            "reasoning": reasoning or {},
            "reasoning_source": reasoning_source,
            "routing_recommendation": routing_recommendation or {},
            "routing_source": routing_source,
            "routing_decision": routing_decision or {},
            "route_choice": route_choice,
            "recent_tool_calls": recent_tool_calls,
            "bandit_decision": bandit_decision or {},
            "trace_log": [trace_entry],
        }

    async def _knowledge_node(self, state: CoordinatorState) -> Dict:
        """??????"""
        start = time.perf_counter()
        try:
            exec_result = await self.tool_executor.execute(
                "knowledge_retriever",
                {"query": state["user_message"], "top_k": 3},
                caller_role=AgentType.SESSION_DIRECTOR.value,
                tool_call_id=self._make_tool_call_id("knowledge_retriever", state),
            )
            prior_results = list(state.get("tool_results") or [])
            prior_outputs = list(state.get("tool_outputs") or [])
            tool_results = prior_results + ([exec_result["result"]] if exec_result["ok"] else [])
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "tool_results": tool_results,
                "tool_outputs": prior_outputs + [exec_result],
                "trace_log": [
                    build_trace_event(
                        node="knowledge",
                        status="ok" if exec_result["ok"] else "error",
                        source=exec_result.get("audit", {}).get("status"),
                        latency_ms=latency_ms,
                        detail={"retrieved": len(tool_results)},
                    )
                ],
            }
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "tool_results": list(state.get("tool_results") or []),
                "tool_outputs": list(state.get("tool_outputs") or []),
                "trace_log": [
                    build_trace_event(
                        node="knowledge",
                        status="error",
                        latency_ms=latency_ms,
                        detail={"error": str(e)},
                    )
                ],
            }

    async def _npc_node(self, state: CoordinatorState) -> Dict:
        """NPC 节点：生成客户回复，输出经 NPCAgentOutput Schema 校验"""
        session_id = str(state.get("session_id", ""))
        async with node_span("npc", {"session_id": session_id}):
            start = time.perf_counter()

            # Inject retrieved memories into history so the NPC can reference past interactions
            base_history = list(state.get("history", []))
            memory_context = state.get("memory_context", [])
            if memory_context:
                memory_lines = []
                for m in memory_context:
                    content = m.get("content", "")
                    mtype = m.get("memory_type", "episodic")
                    importance = m.get("importance", 0.5)
                    if content:
                        memory_lines.append(f"[{mtype}|importance={importance:.2f}] {content}")
                if memory_lines:
                    memory_prefix = "[记忆参考 - 以下是与本次对话相关的历史记忆，可用于保持对话一致性]\n" + "\n".join(memory_lines)
                    base_history = [{"role": "system", "content": memory_prefix}] + base_history

            npc_resp = await self.npc_agent.generate_response(
                message=state["user_message"],
                history=base_history,
                persona=state.get("persona", self.persona),
                stage=state.get("fsm_state", {}).get("current_stage", "discovery")
            )
            # Schema 校验：统一 Agent 输出格式
            from ...schemas.agent_io import validate_npc_output
            validated = validate_npc_output(
                {"content": npc_resp.content, "mood": npc_resp.mood}
            )
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

        return {
            "npc_response": validated.content,
            "npc_mood": validated.mood,
            "trace_log": [
                build_trace_event(
                    node="npc",
                    latency_ms=latency_ms,
                    detail={"response_len": len(validated.content)},
                )
            ],
        }

    async def _coach_node(self, state: CoordinatorState) -> Dict:
        """
        Coach 节点 (Enhanced with Graceful Degradation)
        输出经 CoachAgentOutput Schema 校验

        Fallback Strategy:
        1. Try AI-generated advice first
        2. If AI returns empty or fails -> Use intent-based fallback
        3. If no intent match -> Use default fallback
        4. Track advice source (ai/fallback/error_fallback) for monitoring
        """
        session_id = str(state.get("session_id", ""))
        intent = state.get("intent", "unknown")
        async with node_span("coach", {"session_id": session_id, "intent": intent}):
            return await self._coach_node_impl(state)

    async def _coach_node_impl(self, state: CoordinatorState) -> Dict:
        """Inner coach logic extracted so node_span wraps the whole method."""
        start = time.perf_counter()
        advice_source = "ai"
        advice_text = ""
        advice_tips = []

        # Build history with memory context prepended so coach advice is grounded in past turns
        base_history = list(state.get("history", []))
        memory_context = state.get("memory_context", [])
        if memory_context:
            memory_lines = []
            for m in memory_context:
                content = m.get("content", "")
                mtype = m.get("memory_type", "episodic")
                importance = m.get("importance", 0.5)
                if content:
                    memory_lines.append(f"[{mtype}|importance={importance:.2f}] {content}")
            if memory_lines:
                memory_prefix = "[历史记忆参考 - 教练建议应基于以下上下文]\n" + "\n".join(memory_lines)
                base_history = [{"role": "system", "content": memory_prefix}] + base_history

        try:
            advice_obj = await self.coach_agent.get_advice(
                history=base_history + [
                    {"role": "user", "content": state["user_message"]}
                ],
                session_id=state.get("session_id", "default"),
                turn_number=state.get("turn_number", 1)
            )

            # Schema 校验：统一 Coach 输出格式
            from ...schemas.agent_io import validate_coach_output
            validated = validate_coach_output(advice_obj)
            advice_text = f"{validated.action_advice}\n\n示例话术: {validated.script_example}"
            if validated.compliance_risk and validated.compliance_risk.risk_level != "low":
                advice_text += f"\n\n⚠️ 合规提示: {validated.compliance_risk.warning_message}"
            advice_source = "ai"
            logger.info("[Coach] AI-generated advice used (validated)")

        except Exception as e:
            logger.warning(f"[Coach] AI failed, using fallback: {e}")
            intent = state.get("intent", "default")
            fallback_entry = FALLBACK_COACH_ADVICE.get(
                intent,
                FALLBACK_COACH_ADVICE["error_fallback"]
            )

            advice_text = fallback_entry["advice"]
            advice_tips = fallback_entry.get("tips", [])
            advice_source = "fallback" if intent in FALLBACK_COACH_ADVICE else "error_fallback"

            logger.info(
                f"[Coach] Using {advice_source} advice for intent={intent}"
            )

        if advice_tips:
            formatted_advice = f"{advice_text}\n\nTIP:\n" + "\n".join(
                f"  - {tip}" for tip in advice_tips
            )
        else:
            formatted_advice = advice_text

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        trace = build_trace_event(
            node="coach",
            source=advice_source,
            latency_ms=latency_ms,
            detail={"intent": state.get("intent", "unknown"), "has_advice": bool(advice_text)},
        )

        return {
            "coach_advice": formatted_advice,
            "advice_source": advice_source,
            "trace_log": [trace],
        }

    async def _compliance_node(self, state: CoordinatorState) -> Dict:
        """合规节点：关键词合规检查 + Constitutional AI 价值对齐修正"""
        start = time.perf_counter()
        exec_result = await self.tool_executor.execute(
            "compliance_check",
            {
                "text": state.get("npc_response", ""),
                "stage": state.get("fsm_state", {}).get("current_stage"),
                "context": {"session_id": state.get("session_id")},
            },
            caller_role=AgentType.COMPLIANCE.value,
            tool_call_id=self._make_tool_call_id("compliance_check", state),
        )
        result = exec_result["result"] if exec_result["ok"] else {"risk_level": "ERROR", "risk_flags": []}
        risk_level = result.get("risk_level", "ERROR")
        risk_score = 0.0
        if risk_level == "WARN":
            risk_score = 0.6
        elif risk_level == "BLOCK":
            risk_score = 0.9
        result["risk_score"] = risk_score
        is_compliant = risk_level == "OK"

        # Constitutional AI: if compliance flagged a risk, attempt value-aligned revision
        # ConstitutionalAI rewrites the NPC response to remove violations while preserving intent
        revised_npc_response = state.get("npc_response", "")
        cai_detail: Dict = {}
        if not is_compliant and revised_npc_response:
            try:
                from ...ai_core.constitutional.constitutional_ai import ConstitutionalAI
                cai = ConstitutionalAI(llm_client=getattr(self, "model_gateway", None))
                cai_result = await cai.constitutional_generate(
                    initial_response=revised_npc_response,
                    context={
                        "session_id": state.get("session_id", ""),
                        "risk_level": risk_level,
                        "risk_flags": result.get("risk_flags", []),
                        "stage": state.get("fsm_state", {}).get("current_stage", ""),
                    },
                )
                if cai_result.get("aligned"):
                    revised_npc_response = cai_result["final_response"]
                    risk_score = max(0.0, risk_score - 0.3)  # partial credit for aligned revision
                    cai_detail = {
                        "cai_aligned": True,
                        "cai_iterations": cai_result.get("iterations", 0),
                        "cai_score": cai_result.get("alignment_score", 0.0),
                    }
                    logger.info("[Compliance] ConstitutionalAI revised NPC response (score=%.2f)",
                                cai_result.get("alignment_score", 0.0))
                else:
                    cai_detail = {"cai_aligned": False}
            except Exception as _cai_exc:
                logger.warning("[Compliance] ConstitutionalAI failed: %s", _cai_exc)

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        prior_outputs = list(state.get("tool_outputs") or [])
        return {
            "npc_response": revised_npc_response,
            "compliance_result": result,
            "risk_score": risk_score,
            "tool_outputs": prior_outputs + [exec_result],
            "trace_log": [
                build_trace_event(
                    node="compliance",
                    status="ok" if is_compliant else "warn",
                    source=exec_result.get("audit", {}).get("status"),
                    latency_ms=latency_ms,
                    detail={"risk_level": risk_level, "risk_score": risk_score, **cai_detail},
                )
            ],
        }

    async def _tools_node(self, state: CoordinatorState) -> Dict:
        """??????????"""
        start = time.perf_counter()
        intent = state.get("intent", "")
        results = list(state.get("tool_results") or [])
        tool_outputs = list(state.get("tool_outputs") or [])

        if intent in ["price_inquiry", "product_inquiry"]:
            try:
                exec_result = await self.tool_executor.execute(
                    "knowledge_retriever",
                    {"query": state["user_message"], "top_k": 3},
                    caller_role=AgentType.SESSION_DIRECTOR.value,
                    tool_call_id=self._make_tool_call_id("knowledge_retriever", state),
                )
                tool_outputs.append(exec_result)
                if exec_result["ok"]:
                    results.append(exec_result["result"])
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "tool_results": results,
            "tool_outputs": tool_outputs,
            "trace_log": [
                build_trace_event(
                    node="tools",
                    status="ok",
                    latency_ms=latency_ms,
                    detail={"executed": len(results)},
                )
            ],
        }

    async def execute_turn(
        self,
        turn_number: int,
        user_message: str,
        history: list,
        fsm_state: dict,
        session_id: str = "default",
        skip_coach: bool = False
    ) -> Dict[str, Any]:
        """
        执行一轮对话

        Args:
            turn_number: Turn number
            user_message: User input
            history: Conversation history
            fsm_state: FSM state
            session_id: Session ID
            skip_coach: If True, skip coach node for TTFT optimization (先答后评)

        Returns:
            Dict with NPC reply and optional coach advice
        """
        # ------------------------------------------------------------------
        # Memory: retrieve relevant context for this turn.
        # Lazily initialise AgentMemory for the session on first call.
        # ------------------------------------------------------------------
        memory_context: list = []
        try:
            if session_id not in self._session_memories:
                from ...agents.memory.agent_memory import AgentMemory
                mem = await AgentMemory.create_with_backends(agent_id="coordinator")
                await mem.load_session(session_id)
                self._session_memories[session_id] = mem
            mem = self._session_memories[session_id]
            relevant = await mem.retrieve_relevant(query=user_message, top_k=5)
            memory_context = [r.to_dict() for r in relevant]
        except Exception as _mem_exc:
            logger.warning("[DynamicWorkflow] Memory retrieval failed: %s", _mem_exc)

        initial_state = CoordinatorState(
            user_message=user_message,
            session_id=session_id,
            turn_number=turn_number,
            history=history,
            fsm_state=fsm_state,
            persona=self.persona,
            memory_context=memory_context,
            trace_log=[],
            tool_outputs=[],
            tool_results=[],
            reasoning={},
            reasoning_source="",
            routing_recommendation={},
            routing_source="",
            routing_decision={},
            route_choice="",
            recent_tool_calls=False,
            bandit_decision={},
        )

        # If skip_coach is enabled, temporarily remove coach from enabled nodes
        original_enabled_nodes = None
        original_routing_rules = None
        original_conditional = None
        if skip_coach and NodeType.COACH in self.config.enabled_nodes:
            original_enabled_nodes = self.config.enabled_nodes.copy()
            original_routing_rules = {k: list(v) for k, v in self.config.routing_rules.items()}
            original_conditional = {k: dict(v) for k, v in self.config.conditional_routing.items()}

            enabled_names = {n.value if hasattr(n, "value") else str(n) for n in self.config.enabled_nodes}
            enabled_names.discard(NodeType.COACH.value)

            # Temporarily disable coach
            self.config.enabled_nodes = {
                n for n in self.config.enabled_nodes if n != NodeType.COACH
            }

            # Patch routing to bypass coach
            patched_rules = {}
            for from_node, to_nodes in original_routing_rules.items():
                from_name = from_node.value if hasattr(from_node, "value") else str(from_node)
                if from_name == NodeType.COACH.value:
                    continue
                filtered = []
                for target in to_nodes:
                    target_name = target.value if hasattr(target, "value") else str(target)
                    if target_name == NodeType.COACH.value:
                        continue
                    filtered.append(target_name)
                if not filtered and NodeType.COMPLIANCE.value in enabled_names:
                    filtered = [NodeType.COMPLIANCE.value]
                if filtered:
                    patched_rules[from_name] = filtered
            self.config.routing_rules = patched_rules

            patched_conditional = {}
            for from_node, conditions in original_conditional.items():
                from_name = from_node.value if hasattr(from_node, "value") else str(from_node)
                if from_name == NodeType.COACH.value:
                    continue
                new_conditions = {}
                for key, target in conditions.items():
                    target_name = target.value if hasattr(target, "value") else str(target)
                    if target_name == NodeType.COACH.value:
                        continue
                    new_conditions[key] = target_name
                if new_conditions:
                    patched_conditional[from_name] = new_conditions
            self.config.conditional_routing = patched_conditional

            # Rebuild graph without coach
            self.graph = self._build_dynamic_graph()
            self.app = self.graph.compile()
            logger.info("[TTFT Optimization] Coach node skipped for immediate response")

        try:
            final_state = await self.app.ainvoke(initial_state)

            # --- Bandit reward 闭环 ---
            # 从当轮状态信号计算 per-turn reward，自动回写 LinUCB
            # LLMRewardService (LLM-as-Judge) replaces the rule-based heuristic when available,
            # providing richer signal: task_progress, quality, satisfaction, efficiency, compliance.
            bandit_decision = final_state.get("bandit_decision", {})
            decision_id = bandit_decision.get("decision_id") if bandit_decision else None
            if decision_id and self.bandit:
                reward = self._compute_turn_reward(final_state)
                try:
                    from ...services.llm_reward_service import llm_reward_service
                    llm_result = await llm_reward_service.score_turn(
                        history=list(final_state.get("history", [])),
                        sales_response=user_message,
                        customer_response=final_state.get("npc_response", ""),
                        session_id=session_id,
                    )
                    # Normalise LLM score (0-10) to [-1, 1] to match bandit reward range
                    reward = round((llm_result.overall / 10.0) * 2.0 - 1.0, 4)
                    logger.debug("[Bandit] LLM reward=%.3f reasoning=%s", reward, llm_result.reasoning)
                except Exception as _reward_exc:
                    logger.debug("[Bandit] LLM reward failed, using heuristic: %s", _reward_exc)
                self.bandit.record_feedback(decision_id, reward)
                logger.debug("[Bandit] Auto reward recorded: decision=%s reward=%.3f", decision_id, reward)

            # --- Memory: store this turn's interaction ---
            try:
                if session_id in self._session_memories:
                    mem = self._session_memories[session_id]
                    npc_reply = final_state.get("npc_response", "")
                    await mem.store_interaction(
                        session_id=session_id,
                        turn_number=turn_number,
                        user_message=user_message,
                        npc_response=npc_reply,
                        metadata={
                            "intent": final_state.get("intent", ""),
                            "npc_mood": final_state.get("npc_mood", 0.5),
                            "fsm_stage": fsm_state.get("current_stage", ""),
                        },
                    )
            except Exception as _mem_store_exc:
                logger.warning("[DynamicWorkflow] Memory store failed: %s", _mem_store_exc)

            return {
                "npc_reply": final_state.get("npc_response", ""),
                "npc_mood": final_state.get("npc_mood", 0.5),
                "coach_advice": final_state.get("coach_advice") if not skip_coach else None,
                "intent": final_state.get("intent"),
                "trace": final_state.get("trace_log", []),
                "bandit_decision": bandit_decision,
                "tool_outputs": final_state.get("tool_outputs", []),
                "tool_results": final_state.get("tool_results", []),
            }
        finally:
            # Restore original configuration
            if original_enabled_nodes is not None:
                self.config.enabled_nodes = original_enabled_nodes
                if original_routing_rules is not None:
                    self.config.routing_rules = original_routing_rules
                if original_conditional is not None:
                    self.config.conditional_routing = original_conditional
                self.graph = self._build_dynamic_graph()
                self.app = self.graph.compile()

    async def close_session(self, session_id: str) -> None:
        """
        Flush and tear down the AgentMemory for a session.

        Call this when a training session ends (e.g., from production_coordinator
        or the sessions endpoint) to persist episodic memories to the L1/L2 backends
        and free the in-process cache entry.

        Usage:
            await coordinator.close_session(session_id)
        """
        mem = self._session_memories.pop(session_id, None)
        if mem is not None:
            try:
                await mem.save_session(session_id)
                logger.info("[DynamicWorkflow] Memory session saved: %s", session_id)
            except Exception as exc:
                logger.warning("[DynamicWorkflow] Memory save failed for %s: %s", session_id, exc)

    def _compute_turn_reward(self, state: "CoordinatorState") -> float:
        """
        Compute per-turn bandit reward from state signals.

        Reward formula (maps to -1..1):
          task_completion  * 0.40  (NPC reached Completed/Closed stage)
          response_quality * 0.30  (npc_mood as quality proxy)
          compliance       * 0.20  (no violations = 1.0, blocked = -1.0)
          efficiency       * 0.10  (fewer tool calls = more efficient)

        Raw weighted sum is in [0, 1]; mapped to [-1, 1] via: reward = 2*score - 1
        """
        # Task completion: FSM reached terminal success state
        fsm = state.get("fsm_state") or {}
        final_stage = str(fsm.get("current_stage", "")).lower()
        task_score = 1.0 if final_stage in {"completed", "closed", "closing"} else 0.5

        # Response quality: npc_mood (0..1) as proxy
        quality_score = float(state.get("npc_mood") or 0.5)

        # Compliance: risk_score already in [0, 1]; invert so 0 risk = 1.0 score
        risk = float(state.get("risk_score") or 0.0)
        compliance_score = max(0.0, 1.0 - risk)

        # Efficiency: penalise extra tool calls (0 calls = 1.0, 3+ calls = 0.0)
        tool_calls = state.get("tool_calls") or []
        efficiency_score = max(0.0, 1.0 - len(tool_calls) / 3.0)

        weighted = (
            task_score       * 0.40
            + quality_score  * 0.30
            + compliance_score * 0.20
            + efficiency_score * 0.10
        )
        # Map [0, 1] → [-1, 1]
        return round(2.0 * weighted - 1.0, 4)

    async def record_bandit_feedback(
        self,
        decision_id: str,
        reward: float,
        signals: Optional[Dict[str, float]] = None,
    ) -> bool:
        if not self.bandit or not decision_id:
            return False
        return bool(self.bandit.record_feedback(decision_id, reward, signals))


# ==================== 预定义配置模板 ====================

def get_minimal_config() -> WorkflowConfig:
    """最小化配置（仅Intent + NPC）"""
    settings = get_settings()
    return WorkflowConfig(
        name="minimal_workflow",
        enabled_nodes={NodeType.INTENT, NodeType.NPC},
        routing_rules={"intent": ["npc"]},
        description="Minimal workflow: Intent -> NPC",
        enable_reasoning=False,
        enable_routing_policy=False,
        enable_bandit=settings.BANDIT_ROUTING_ENABLED
    )


def get_full_config() -> WorkflowConfig:
    """完整配置（全部节点）"""
    settings = get_settings()
    return WorkflowConfig(
        name="full_workflow",
        enabled_nodes={
            NodeType.INTENT,
            NodeType.KNOWLEDGE,
            NodeType.NPC,
            NodeType.COACH,
            NodeType.COMPLIANCE
        },
        conditional_routing={
            "intent": {
                "knowledge": "knowledge",
                "npc": "npc"
            }
        },
        routing_rules={
            "knowledge": ["npc"],
            "npc": ["coach"],
            "coach": ["compliance"]
        },
        description="Full workflow with all nodes enabled",
        enable_reasoning=True,
        enable_routing_policy=True,
        enable_bandit=settings.BANDIT_ROUTING_ENABLED
    )


def get_ab_test_configs() -> Dict[str, WorkflowConfig]:
    """A/B测试配置组"""
    return {
        "variant_A": WorkflowConfig(
            name="ab_test_control",
            enabled_nodes={NodeType.INTENT, NodeType.NPC},
            routing_rules={"intent": ["npc"]},
            description="Control group: No Coach",
            enable_reasoning=False,
            enable_routing_policy=False,
            enable_bandit=settings.BANDIT_ROUTING_ENABLED
        ),
        "variant_B": WorkflowConfig(
            name="ab_test_experiment",
            enabled_nodes={NodeType.INTENT, NodeType.NPC, NodeType.COACH},
            routing_rules={
                "intent": ["npc"],
                "npc": ["coach"]
            },
            description="Experiment group: With Coach",
            enable_reasoning=False,
            enable_routing_policy=False,
            enable_bandit=settings.BANDIT_ROUTING_ENABLED
        )
    }
