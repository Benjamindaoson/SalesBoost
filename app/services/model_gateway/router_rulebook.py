"""
Router Rulebook - 硬规则实现
HR-1~HR-4 硬规则逻辑
"""
import logging
from typing import Optional
from app.services.model_gateway.schemas import (
    RoutingContext,
    RoutingDecision,
    AgentType,
    LatencyMode,
    ProviderType,
)

logger = logging.getLogger(__name__)


class RouterRulebook:
    """Router Rulebook - 硬规则集合"""
    
    # HR-1: 硬预算阈值
    HARD_BUDGET_PER_TURN = 0.01  # $0.01
    
    # HR-3: 低置信度阈值
    LOW_CONFIDENCE_THRESHOLD = 0.6
    
    @staticmethod
    def apply_hard_rules(
        context: RoutingContext,
        initial_decision: RoutingDecision,
        budget_remaining: float,
        retrieval_confidence: Optional[float] = None,
    ) -> RoutingDecision:
        """
        应用硬规则 HR-1~HR-4
        
        Args:
            context: 路由上下文
            initial_decision: 初始路由决策
            budget_remaining: 剩余预算
            retrieval_confidence: 检索置信度
            
        Returns:
            应用硬规则后的路由决策
        """
        decision = initial_decision
        downgrade_reasons = []
        
        # HR-1: 预算熔断
        if budget_remaining < RouterRulebook.HARD_BUDGET_PER_TURN:
            # 禁 STRONG_*（GPT-4）
            if "gpt-4" in decision.model.lower() or decision.provider == ProviderType.OPENAI:
                decision = RouterRulebook._downgrade_to_cheap(decision, context)
                downgrade_reasons.append("HR-1:BudgetCritical")
                logger.warning(f"HR-1: Budget critical (${budget_remaining:.4f}), downgraded to {decision.model}")
        
        # HR-2: 快路径不可阻塞
        if context.latency_mode == LatencyMode.FAST:
            # 禁 STRONG_CHAT（GPT-4）
            if "gpt-4" in decision.model.lower():
                decision = RouterRulebook._downgrade_to_fast(decision, context)
                downgrade_reasons.append("HR-2:FastPath")
                logger.info(f"HR-2: Fast path, downgraded from GPT-4 to {decision.model}")
        
        # HR-3: 低置信度禁止确定性强回答
        if retrieval_confidence is not None and retrieval_confidence < RouterRulebook.LOW_CONFIDENCE_THRESHOLD:
            # 禁 STRONG_CHAT（GPT-4）
            if "gpt-4" in decision.model.lower():
                decision = RouterRulebook._downgrade_to_cheap(decision, context)
                downgrade_reasons.append(f"HR-3:LowConfidence({retrieval_confidence:.2f})")
                logger.info(f"HR-3: Low confidence ({retrieval_confidence:.2f}), downgraded from GPT-4")
        
        # HR-4: Evaluator 一致性（在 Router 中处理，这里只是记录）
        if context.agent_type == AgentType.EVALUATOR:
            # 确保使用固定模型（已在 Router 中处理）
            logger.debug(f"HR-4: Evaluator using fixed model: {decision.model}")
        
        # 更新决策理由
        if downgrade_reasons:
            decision.reason += f", Rules: {', '.join(downgrade_reasons)}"
        
        return decision
    
    @staticmethod
    def _downgrade_to_cheap(decision: RoutingDecision, context: RoutingContext) -> RoutingDecision:
        """降级到最便宜模型"""
        # 优先使用 Mock（测试）或 Qwen Turbo
        cheap_provider = ProviderType.MOCK
        cheap_model = "mock"
        
        # 如果有 Qwen Turbo，使用它
        if context.budget_remaining >= 0.001:  # 至少需要一点预算
            cheap_provider = ProviderType.QWEN
            cheap_model = "qwen-turbo"
        
        return RoutingDecision(
            provider=cheap_provider,
            model=cheap_model,
            reason=decision.reason + ", DowngradedToCheap",
            estimated_cost=0.001,
            estimated_latency_ms=1000.0,
            fallback_provider=decision.fallback_provider,
            fallback_model=decision.fallback_model,
        )
    
    @staticmethod
    def _downgrade_to_fast(decision: RoutingDecision, context: RoutingContext) -> RoutingDecision:
        """降级到快速模型"""
        # 优先使用 Qwen Turbo（快速）
        fast_provider = ProviderType.QWEN
        fast_model = "qwen-turbo"
        
        return RoutingDecision(
            provider=fast_provider,
            model=fast_model,
            reason=decision.reason + ", DowngradedToFast",
            estimated_cost=0.001,
            estimated_latency_ms=1000.0,
            fallback_provider=decision.fallback_provider,
            fallback_model=decision.fallback_model,
        )
