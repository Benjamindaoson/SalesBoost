"""
AI Cost Control System - AI成本控制系统
提供模型路由优化、Token预算管理、实时成本监控
"""

import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from asyncio import Semaphore

from app.core.config import get_settings
from app.core.llm_router import LLMRouter
from app.schemas.fsm import FSMState, SalesStage
from app.models.config_models import ScenarioConfig, CustomerPersona

settings = get_settings()


class ModelTier(Enum):
    """模型层级定义"""

    CHEAP = "cheap"  # $0.001/1K tokens
    STANDARD = "standard"  # $0.01/1K tokens
    PREMIUM = "premium"  # $0.1/1K tokens
    FLAGSHIP = "flagship"  # $1.0/1K tokens


@dataclass
class ModelInfo:
    """模型信息"""

    name: str
    tier: ModelTier
    cost_per_1k_tokens: float
    max_tokens: int
    capabilities: List[str]
    latency_ms: float = 0


@dataclass
class CostRecord:
    """成本记录"""

    id: str
    model_name: str
    model_tier: ModelTier
    tokens_used: int
    cost_usd: float
    latency_ms: float
    session_id: str
    user_id: str
    timestamp: float
    agent_type: str


class ModelCostCalculator:
    """模型成本计算器"""

    # 模型定价表 (每1K tokens)
    MODEL_PRICING = {
        # OpenAI models
        "gpt-4": 0.03,  # $0.03/1K input, $0.06/1K output
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.001,
        # 中国大模型 (更便宜)
        "qwen-turbo": 0.0003,  # 阿里通义千问 Turbo
        "qwen-plus": 0.004,  # 阿里通义千问 Plus
        "qwen-max": 0.04,  # 阿里通义千问 Max
        "glm-4-flash": 0.0001,  # 智谱 GLM-4 Flash
        "glm-4": 0.05,  # 智谱 GLM-4
        "deepseek": 0.014,  # DeepSeek
    }

    @classmethod
    def calculate_cost(cls, model_name: str, input_tokens: int, output_tokens: int = 0) -> float:
        """计算调用成本"""
        base_cost = cls.MODEL_PRICING.get(model_name, 0.01)  # 默认$0.01/1K

        # 简化计算：假设input和output成本相同
        total_tokens = input_tokens + output_tokens
        cost = (total_tokens / 1000) * base_cost

        return round(cost, 6)

    @classmethod
    def get_model_tier(cls, model_name: str) -> ModelTier:
        """获取模型层级"""
        cost = cls.MODEL_PRICING.get(model_name, 0.01)

        if cost < 0.001:
            return ModelTier.CHEAP
        elif cost < 0.01:
            return ModelTier.STANDARD
        elif cost < 0.1:
            return ModelTier.PREMIUM
        else:
            return ModelTier.FLAGSHIP


class SmartModelRouter:
    """智能模型路由器"""

    def __init__(self):
        self.available_models = self._initialize_models()

    def _initialize_models(self) -> List[ModelInfo]:
        """初始化可用模型"""
        return [
            ModelInfo(
                name="gpt-4",
                tier=ModelTier.FLAGSHIP,
                cost_per_1k_tokens=0.03,
                max_tokens=8192,
                capabilities=["reasoning", "analysis"],
                latency_ms=2000,
            ),
            ModelInfo(
                name="gpt-3.5-turbo",
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.001,
                max_tokens=4096,
                capabilities=["conversation", "quick_response"],
                latency_ms=800,
            ),
            ModelInfo(
                name="qwen-turbo",
                tier=ModelTier.CHEAP,
                cost_per_1k_tokens=0.0003,
                max_tokens=6144,
                capabilities=["conversation", "chinese"],
                latency_ms=500,
            ),
            ModelInfo(
                name="qwen-plus",
                tier=ModelTier.STANDARD,
                cost_per_1k_tokens=0.004,
                max_tokens=6144,
                capabilities=["reasoning", "chinese"],
                latency_ms=1000,
            ),
        ]

    async def route_to_optimal_model(
        self, agent_type: str, task_complexity: float = 0.5, budget_limit: Optional[float] = None
    ) -> Tuple[str, ModelInfo]:
        """路由到最优模型"""

        # 过滤模型
        available_models = self._filter_models(self.available_models, budget_limit=budget_limit)

        # 根据复杂度选择模型
        selected_model = self._select_model_by_complexity(available_models, agent_type, task_complexity)

        return selected_model.name, selected_model

    def _filter_models(
        self, models: List[ModelInfo], budget_limit: Optional[float] = None, latency_requirement: Optional[float] = None
    ) -> List[ModelInfo]:
        """根据条件过滤模型"""
        filtered = models.copy()

        if budget_limit is not None:
            # 估算单个调用成本 (假设2000 tokens)
            filtered = [m for m in filtered if (2000 / 1000) * m.cost_per_1k_tokens <= budget_limit]

        if latency_requirement is not None:
            filtered = [m for m in filtered if m.latency_ms <= latency_requirement]

        return filtered if filtered else models  # 至少返回一个模型

    def _select_model_by_complexity(self, models: List[ModelInfo], agent_type: str, complexity: float) -> ModelInfo:
        """根据复杂度选择模型"""

        # 复杂度分级
        if complexity < 0.3:
            # 低复杂度 - 选择便宜模型
            cheap_models = [m for m in models if m.tier in [ModelTier.CHEAP, ModelTier.STANDARD]]
            if cheap_models:
                return min(cheap_models, key=lambda m: m.cost_per_1k_tokens)

        elif complexity < 0.7:
            # 中等复杂度 - 选择标准模型
            standard_models = [m for m in models if m.tier == ModelTier.STANDARD]
            if standard_models:
                return standard_models[0]

        else:
            # 高复杂度 - 选择高级模型
            premium_models = [m for m in models if m.tier in [ModelTier.PREMIUM, ModelTier.FLAGSHIP]]
            if premium_models:
                return premium_models[0]

        # 默认选择第一个
        return models[0]


class BudgetManager:
    """预算管理器"""

    def __init__(self):
        self.session_budgets = {}  # 会话预算
        self.user_budgets = {}  # 用户预算
        self.cost_tracking = {}  # 成本追踪

    def set_session_budget(self, session_id: str, budget_usd: float):
        """设置会话预算"""
        self.session_budgets[session_id] = budget_usd

    def set_user_budget(self, user_id: str, budget_usd: float):
        """设置用户预算"""
        self.user_budgets[user_id] = budget_usd

    def check_budget(self, session_id: str, user_id: str, estimated_cost: float) -> bool:
        """检查预算"""
        session_budget = self.session_budgets.get(session_id, float("inf"))
        user_budget = self.user_budgets.get(user_id, float("inf"))

        available_budget = min(session_budget, user_budget)
        return estimated_cost <= available_budget

    def record_cost(self, session_id: str, cost_usd: float):
        """记录成本"""
        if session_id not in self.cost_tracking:
            self.cost_tracking[session_id] = 0

        self.cost_tracking[session_id] += cost_usd

    def get_session_cost(self, session_id: str) -> float:
        """获取会话总成本"""
        return self.cost_tracking.get(session_id, 0.0)

    def get_user_cost(self, user_id: str) -> float:
        """获取用户总成本"""
        return sum(cost for sid, cost in self.cost_tracking.items() if sid.startswith(f"{user_id}_"))


class CostOptimizedLLMCaller:
    """成本优化的LLM调用器"""

    def __init__(self):
        self.cost_calculator = ModelCostCalculator()
        self.smart_router = SmartModelRouter()
        self.budget_manager = BudgetManager()
        self.llm_router = LLMRouter()
        self.semaphore = Semaphore(10)  # 并发限制

    async def call_with_cost_control(
        self,
        agent_type: str,
        prompt: str,
        session_id: str,
        user_id: str,
        task_complexity: float = 0.5,
        max_budget: Optional[float] = None,
        fallback_enabled: bool = True,
    ) -> Dict:
        """带成本控制的LLM调用"""

        start_time = time.time()
        call_id = str(uuid.uuid4())

        async with self.semaphore:
            try:
                # 获取最优模型
                model_name, model_info = await self.smart_router.route_to_optimal_model(
                    agent_type, task_complexity, max_budget
                )

                # 估算成本
                estimated_tokens = len(prompt.split()) * 1.3  # 粗略估算
                estimated_cost = self.cost_calculator.calculate_cost(model_name, int(estimated_tokens))

                # 检查预算
                if not self.budget_manager.check_budget(session_id, user_id, estimated_cost):
                    if not fallback_enabled:
                        raise Exception("Budget exceeded and fallback disabled")

                    # 降级到更便宜的模型
                    fallback_model = settings.LLM_FALLBACK_MODEL
                    model_name = fallback_model
                    estimated_cost = self.cost_calculator.calculate_cost(fallback_model, int(estimated_tokens))

                # 获取LLM实例并调用
                llm_instance = self.llm_router.get_llm_instance(agent_type)

                # 模拟调用（实际应该调用真实的LLM）
                await asyncio.sleep(0.1)
                response = {"content": "模拟响应", "tokens_used": estimated_tokens}

                # 计算实际成本
                latency_ms = (time.time() - start_time) * 1000
                actual_cost = self.cost_calculator.calculate_cost(model_name, response["tokens_used"])

                # 记录成本和指标
                self.budget_manager.record_cost(session_id, actual_cost)

                cost_record = CostRecord(
                    id=call_id,
                    model_name=model_name,
                    model_tier=self.cost_calculator.get_model_tier(model_name),
                    tokens_used=response["tokens_used"],
                    cost_usd=actual_cost,
                    latency_ms=latency_ms,
                    session_id=session_id,
                    user_id=user_id,
                    timestamp=time.time(),
                    agent_type=agent_type,
                )

                return {
                    "response": response,
                    "cost_record": cost_record,
                    "model_used": model_name,
                    "actual_cost": actual_cost,
                    "latency_ms": latency_ms,
                }

            except Exception as e:
                return {"error": str(e), "call_id": call_id, "session_id": session_id, "timestamp": time.time()}


# 全局实例
cost_optimized_caller = CostOptimizedLLMCaller()


# 导出主要类
__all__ = [
    "ModelTier",
    "ModelInfo",
    "CostRecord",
    "ModelCostCalculator",
    "SmartModelRouter",
    "BudgetManager",
    "CostOptimizedLLMCaller",
    "cost_optimized_caller",
]
