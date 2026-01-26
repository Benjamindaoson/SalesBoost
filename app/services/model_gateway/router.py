"""
Model Router - 根据上下文选择最优模型
"""
import logging
from typing import Optional, Dict, Any
from app.services.model_gateway.schemas import (
    RoutingContext,
    RoutingDecision,
    ProviderType,
    AgentType,
    LatencyMode,
    ModelConfig,
)
from app.services.model_gateway.router_rulebook import RouterRulebook
from app.core.config import get_settings
from app.core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class ModelRouter:
    """模型路由器"""
    
    def __init__(self):
        self.settings = get_settings()
        # 模型配置映射
        self.model_configs: Dict[str, ModelConfig] = self._load_model_configs()
    
    def _load_model_configs(self) -> Dict[str, ModelConfig]:
        """加载模型配置"""
        configs: Dict[str, ModelConfig] = {}

        def add_model(model_name: Optional[str], provider: Optional[ProviderType] = None, timeout: float = 30.0) -> None:
            if not model_name:
                return
            selected_provider = provider or self._infer_provider(model_name)
            api_key, base_url = self._get_provider_credentials(selected_provider)
            configs[model_name] = ModelConfig(
                provider=selected_provider,
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                temperature=0.7,
                timeout=timeout,
            )

        model_candidates = {
            getattr(self.settings, "LLM_MODEL_INTENT_GATE", None),
            getattr(self.settings, "LLM_MODEL_NPC", None),
            getattr(self.settings, "LLM_MODEL_COACH", None),
            getattr(self.settings, "LLM_MODEL_EVALUATOR", None),
            getattr(self.settings, "LLM_MODEL_RAG", None),
            getattr(self.settings, "LLM_MODEL_COMPLIANCE", None),
            getattr(self.settings, "LLM_FALLBACK_MODEL", None),
            getattr(self.settings, "OPENAI_MODEL", None),
            "qwen-turbo",
            "qwen-plus",
            "qwen-max",
            "glm-4",
            "glm-4-flash",
            "gpt-3.5-turbo",
            "gpt-4",
            "deepseek-chat",
        }

        for model_name in sorted(m for m in model_candidates if m):
            add_model(model_name)

        configs["mock"] = ModelConfig(
            provider=ProviderType.MOCK,
            model="mock",
            timeout=1.0,
        )

        return configs

    def _infer_provider(self, model_name: str) -> ProviderType:
        model = model_name.lower()
        if model.startswith("qwen"):
            return ProviderType.QWEN
        if model.startswith("glm"):
            return ProviderType.ZHIPU
        if model.startswith("deepseek"):
            return ProviderType.DEEPSEEK
        return ProviderType.OPENAI

    def _get_provider_credentials(self, provider: ProviderType) -> tuple[Optional[str], Optional[str]]:
        if provider == ProviderType.QWEN:
            return (
                getattr(self.settings, "DASHSCOPE_API_KEY", None)
                or getattr(self.settings, "QWEN_API_KEY", None),
                getattr(self.settings, "QWEN_BASE_URL", None),
            )
        if provider == ProviderType.ZHIPU:
            return (
                getattr(self.settings, "ZHIPU_API_KEY", None),
                getattr(self.settings, "ZHIPU_BASE_URL", None),
            )
        if provider == ProviderType.DEEPSEEK:
            return (
                getattr(self.settings, "DEEPSEEK_API_KEY", None),
                getattr(self.settings, "DEEPSEEK_BASE_URL", None),
            )
        return (
            getattr(self.settings, "OPENAI_API_KEY", None),
            getattr(self.settings, "OPENAI_BASE_URL", None),
        )
    
    def route(self, context: RoutingContext) -> RoutingDecision:
        """
        路由决策
        
        策略：
        1. 按 Agent Type 选择默认模型
        2. 按 Turn Importance 升级/降级
        3. 按 Budget 降级
        4. 按 Latency Mode 选择快速/慢速模型
        5. 按 Risk Level 选择强模型
        """
        # 1. 按 Agent Type 选择默认模型
        default_model = self._get_default_model(context.agent_type, context.latency_mode)
        
        # 2. 按 Turn Importance 升级
        if context.turn_importance > 0.8:
            upgraded_model = self._upgrade_model(default_model)
            if upgraded_model:
                default_model = upgraded_model
        
        # 3. 按 Budget 降级
        if context.budget_remaining < 0.01:
            default_model = self._downgrade_model(default_model)
        
        # 4. 按 Risk Level 升级
        if context.risk_level == "high":
            upgraded_model = self._upgrade_model(default_model)
            if upgraded_model:
                default_model = upgraded_model
        
        # 5. 按 Latency Mode 选择快速模型
        if context.latency_mode == LatencyMode.FAST:
            fast_model = self._get_fast_model(context.agent_type)
            if fast_model:
                default_model = fast_model
        
        # 获取模型配置
        model_config = self.model_configs.get(default_model)
        if not model_config:
            # 降级到 Mock
            model_config = self.model_configs["mock"]
            default_model = "mock"
        
        # 估算成本和延迟
        estimated_cost = self._estimate_cost(context.agent_type, model_config.model)
        estimated_latency = self._estimate_latency(model_config, context.latency_mode)
        
        # 选择降级模型（作为 fallback）
        fallback_model = self._downgrade_model(default_model)
        fallback_config = self.model_configs.get(fallback_model)
        
        decision = RoutingDecision(
            provider=model_config.provider,
            model=model_config.model,
            reason=f"Agent={context.agent_type}, Importance={context.turn_importance:.2f}, "
                   f"Budget=${context.budget_remaining:.2f}, Latency={context.latency_mode}",
            estimated_cost=estimated_cost,
            estimated_latency_ms=estimated_latency,
            fallback_provider=fallback_config.provider if fallback_config else None,
            fallback_model=fallback_model if fallback_config else None,
        )
        
        # 应用硬规则 HR-1~HR-4（在路由决策中直接应用）
        # HR-1: 预算熔断
        HARD_BUDGET_PER_TURN = 0.01
        if context.budget_remaining < HARD_BUDGET_PER_TURN:
            if "gpt-4" in decision.model.lower() or decision.provider == ProviderType.OPENAI:
                decision = RoutingDecision(
                    provider=ProviderType.MOCK if context.budget_remaining < 0.001 else ProviderType.QWEN,
                    model="mock" if context.budget_remaining < 0.001 else "qwen-turbo",
                    reason=decision.reason + ", HR-1:BudgetCritical",
                    estimated_cost=0.001,
                    estimated_latency_ms=1000.0,
                    fallback_provider=decision.fallback_provider,
                    fallback_model=decision.fallback_model,
                )
        
        # HR-2: 快路径不可阻塞
        if context.latency_mode == LatencyMode.FAST:
            if "gpt-4" in decision.model.lower():
                decision = RoutingDecision(
                    provider=ProviderType.QWEN,
                    model="qwen-turbo",
                    reason=decision.reason + ", HR-2:FastPath",
                    estimated_cost=0.001,
                    estimated_latency_ms=1000.0,
                    fallback_provider=decision.fallback_provider,
                    fallback_model=decision.fallback_model,
                )
        
        # HR-3: 低置信度禁止确定性强回答
        if context.retrieval_confidence is not None and context.retrieval_confidence < 0.6:
            if "gpt-4" in decision.model.lower() and context.agent_type in [AgentType.COACH_GENERATOR, AgentType.NPC_GENERATOR]:
                decision = RoutingDecision(
                    provider=ProviderType.QWEN,
                    model="qwen-turbo",
                    reason=decision.reason + f", HR-3:LowConfidence({context.retrieval_confidence:.2f})",
                    estimated_cost=0.001,
                    estimated_latency_ms=1000.0,
                    fallback_provider=decision.fallback_provider,
                    fallback_model=decision.fallback_model,
                )
        
        # HR-4: Evaluator 一致性（在 Router 类中处理，使用实例变量）
        if context.agent_type == AgentType.EVALUATOR:
            if not hasattr(self, '_evaluator_fixed_model'):
                self._evaluator_fixed_model = decision.model
            else:
                # 强制使用固定模型
                fixed_config = self.model_configs.get(self._evaluator_fixed_model)
                if fixed_config:
                    decision = RoutingDecision(
                        provider=fixed_config.provider,
                        model=self._evaluator_fixed_model,
                        reason=decision.reason + ", HR-4:FixedModel",
                        estimated_cost=decision.estimated_cost,
                        estimated_latency_ms=decision.estimated_latency_ms,
                        fallback_provider=decision.fallback_provider,
                        fallback_model=decision.fallback_model,
                    )
        
        logger.info(f"Routing decision: {decision.provider}/{decision.model} for {context.agent_type}")
        return decision
    
    def _get_default_model(self, agent_type: AgentType, latency_mode: LatencyMode) -> str:
        """获取默认模型"""
        settings = self.settings
        defaults = {
            AgentType.INTENT_GATE: getattr(settings, "LLM_MODEL_INTENT_GATE", "qwen-turbo"),
            AgentType.RAG: getattr(settings, "LLM_MODEL_RAG", "glm-4-flash"),
            AgentType.COMPLIANCE: getattr(settings, "LLM_MODEL_COMPLIANCE", "qwen-turbo"),
            AgentType.NPC: getattr(settings, "LLM_MODEL_NPC", "qwen-plus"),
            AgentType.COACH: getattr(settings, "LLM_MODEL_COACH", "qwen-max"),
            AgentType.SESSION_DIRECTOR: getattr(settings, "LLM_MODEL_INTENT_GATE", "qwen-turbo"),
            AgentType.RETRIEVER: getattr(settings, "LLM_MODEL_RAG", "glm-4-flash"),
            AgentType.NPC_GENERATOR: getattr(settings, "LLM_MODEL_NPC", "qwen-plus"),
            AgentType.COACH_GENERATOR: getattr(settings, "LLM_MODEL_COACH", "qwen-max"),
            AgentType.EVALUATOR: getattr(settings, "LLM_MODEL_EVALUATOR", "glm-4"),
            AgentType.ADOPTION_TRACKER: getattr(settings, "LLM_MODEL_COMPLIANCE", "qwen-turbo"),
            AgentType.STRATEGY: getattr(settings, "LLM_MODEL_COACH", "qwen-max"),
        }
        default_model = defaults.get(agent_type, "qwen-turbo")
        if latency_mode == LatencyMode.FAST and default_model in {"qwen-max", "glm-4", "gpt-4"}:
            return getattr(settings, "LLM_MODEL_INTENT_GATE", "qwen-turbo")
        return default_model
    
    def _get_fast_model(self, agent_type: AgentType) -> Optional[str]:
        """获取快速模型"""
        fast_models = {
            AgentType.NPC: "qwen-turbo",
            AgentType.NPC_GENERATOR: "qwen-turbo",
            AgentType.RETRIEVER: "qwen-turbo",
            AgentType.SESSION_DIRECTOR: "qwen-turbo",
            AgentType.INTENT_GATE: "qwen-turbo",
            AgentType.COMPLIANCE: "qwen-turbo",
        }
        model_name = fast_models.get(agent_type)
        if model_name and model_name in self.model_configs:
            return model_name
        return None
    
    def _upgrade_model(self, current_model: str) -> Optional[str]:
        """升级模型"""
        upgrades = {
            "qwen-turbo": "qwen-plus",
            "qwen-plus": "qwen-max",
            "glm-4-flash": "glm-4",
            "gpt-3.5-turbo": "gpt-4",
        }
        upgraded = upgrades.get(current_model)
        if upgraded and upgraded in self.model_configs:
            return upgraded
        return None
    
    def _downgrade_model(self, current_model: str) -> str:
        """降级模型"""
        downgrades = {
            "gpt-4": "gpt-3.5-turbo",
            "qwen-max": "qwen-plus",
            "qwen-plus": "qwen-turbo",
            "glm-4": "glm-4-flash",
            "deepseek-chat": "qwen-turbo",
        }
        downgraded = downgrades.get(current_model, "qwen-turbo")
        if downgraded in self.model_configs:
            return downgraded
        return "mock"
    
    def _estimate_cost(self, agent_type: AgentType, model: str) -> float:
        """估算成本（美元）"""
        base_costs = {
            "gpt-4": 0.05,
            "gpt-3.5-turbo": 0.002,
            "qwen-plus": 0.003,
            "qwen-turbo": 0.001,
            "qwen-max": 0.02,
            "glm-4": 0.05,
            "glm-4-flash": 0.001,
            "deepseek-chat": 0.0007,
            "mock": 0.0,
        }
        for model_key, cost in base_costs.items():
            if model_key in model.lower():
                return cost
        return 0.001
    
    def _estimate_latency(self, model_config: ModelConfig, latency_mode: LatencyMode) -> float:
        """估算延迟（毫秒）"""
        # 基于 Provider 和 Latency Mode 估算
        if latency_mode == LatencyMode.FAST:
            return 1000.0  # 1s
        else:
            return 3000.0  # 3s
