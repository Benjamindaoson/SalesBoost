"""
Model Gateway - 统一模型调用入口
"""
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.model_gateway.schemas import (
    RoutingContext,
    RoutingDecision,
    ModelCall,
    AgentType,
    LatencyMode,
    ProviderType,
    ModelConfig,
)
from app.services.model_gateway.router import ModelRouter
from app.services.model_gateway.budget import BudgetManager
from app.services.model_gateway.providers import create_provider
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.prefix_cache import PromptCache

logger = logging.getLogger(__name__)


class ModelGateway:
    """模型网关 - 统一入口"""
    
    def __init__(self, budget_manager: Optional[BudgetManager] = None):
        self.router = ModelRouter()
        self.budget_manager = budget_manager or BudgetManager()
        # Provider 缓存：provider_type -> BaseProvider
        self.provider_cache: Dict[str, BaseProvider] = {}
        self.prompt_cache = PromptCache()
        # 调用统计
        self.call_stats: Dict[str, int] = {}
        # 指标追踪
        self.metrics = {
            "downgrade_count": 0,
            "downgrade_reasons": [],
        }
    
    async def chat(
        self,
        agent_type: AgentType,
        messages: List[Dict[str, str]],
        context: RoutingContext,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_prompt_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        聊天调用
        
        Returns:
            {
                "content": str,
                "usage": {...},
                "model": str,
                "call_id": str,
                "cost_usd": float,
                "latency_ms": float,
            }
        """
        call_id = str(uuid.uuid4())
        start_time = time.time()
        used_fallback = False
        downgrade_reason = None
        
        try:
            # 1. 路由决策
            decision = self.router.route(context)

            # 1.1 Prompt Cache (prefix/response cache)
            cache_key = None
            if use_prompt_cache:
                cache_key = self.prompt_cache.build_key(
                    messages=messages,
                    model=decision.model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                cached = self.prompt_cache.get(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    cached["provider"] = decision.provider.value
                    cached["model"] = decision.model
                    return cached
            
            # 2. 检查预算
            is_available, remaining = self.budget_manager.check_budget(
                context.session_id,
                decision.estimated_cost,
                path="fast" if context.latency_mode == LatencyMode.FAST else "slow"
            )
            
            if not is_available:
                # 预算不足，降级到 fallback
                if decision.fallback_provider and decision.fallback_model:
                    logger.warning(f"Budget insufficient, using fallback: {decision.fallback_model}")
                    decision.provider = decision.fallback_provider
                    decision.model = decision.fallback_model
                    used_fallback = True
                    downgrade_reason = "budget_insufficient"
                else:
                    raise RuntimeError(f"Budget insufficient: ${remaining:.4f} remaining")
            
            # 3. 获取 Provider
            provider = await self._get_provider(decision.provider, decision.model)
            
            # 4. 调用模型
            try:
                result = await provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            except Exception as e:
                # 调用失败，尝试 fallback
                if decision.fallback_provider and decision.fallback_model:
                    logger.warning(f"Primary provider failed: {e}, trying fallback")
                    # 指标埋点：downgrade
                    self.metrics["downgrade_count"] = self.metrics.get("downgrade_count", 0) + 1
                    self.metrics["downgrade_reasons"] = self.metrics.get("downgrade_reasons", [])
                    self.metrics["downgrade_reasons"].append(f"provider_error: {str(e)[:50]}")
                    logger.info(
                        f"[METRIC: downgrade_count={self.metrics['downgrade_count']}, "
                        f"downgrade_reason=provider_error]"
                    )
                    
                    fallback_provider = await self._get_provider(
                        decision.fallback_provider,
                        decision.fallback_model
                    )
                    result = await fallback_provider.chat(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    decision.provider = decision.fallback_provider
                    decision.model = decision.fallback_model
                    used_fallback = True
                    downgrade_reason = f"provider_error: {str(e)[:50]}"
                else:
                    raise
            
            # 5. 计算成本和延迟
            latency_ms = (time.time() - start_time) * 1000
            cost_usd = provider.estimate_cost(
                result["usage"]["prompt_tokens"],
                result["usage"]["completion_tokens"],
                decision.model
            )
            
            # 6. 扣减预算
            self.budget_manager.deduct_budget(
                context.session_id,
                cost_usd,
                path="fast" if context.latency_mode == LatencyMode.FAST else "slow"
            )
            remaining_after = self.budget_manager.get_remaining_budget(context.session_id)
            
            # 7. 记录调用
            call = ModelCall(
                call_id=call_id,
                agent_type=agent_type,
                provider=decision.provider,
                model=decision.model,
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                total_tokens=result["usage"]["total_tokens"],
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=True,
                timestamp=datetime.utcnow().isoformat(),
            )
            self.budget_manager.record_call(call)
            
            # 8. 更新统计
            provider_model_key = f"{decision.provider.value}/{decision.model}"
            self.call_stats[provider_model_key] = \
                self.call_stats.get(provider_model_key, 0) + 1
            
            # 9. 指标埋点：provider/model hit, token_usage, estimated_cost
            logger.info(
                f"[METRIC: provider_hit={decision.provider.value}, "
                f"model_hit={decision.model}, "
                f"tokens={result['usage']['total_tokens']}, "
                f"cost=${cost_usd:.4f}, "
                f"latency={latency_ms:.0f}ms]"
            )
            
            # 10. 返回结果
            result["call_id"] = call_id
            result["cost_usd"] = cost_usd
            result["latency_ms"] = latency_ms
            result["provider"] = decision.provider.value
            result["model"] = decision.model
            result["routing_reason"] = decision.reason
            result["budget_remaining"] = remaining_after
            result["downgrade_reason"] = downgrade_reason
            result["fallback_used"] = used_fallback
            result["cache_hit"] = False

            if cache_key:
                self.prompt_cache.set(cache_key, result)
            
            return result
            
        except Exception as e:
            # 记录失败调用和降级
            latency_ms = (time.time() - start_time) * 1000
            
            # 记录降级
            logger.warning(
                f"[METRIC] Downgrade: {agent_type.value} -> error, "
                f"reason={str(e)[:100]}, latency={latency_ms:.0f}ms"
            )
            
            call = ModelCall(
                call_id=call_id,
                agent_type=agent_type,
                provider=ProviderType.MOCK,
                model="error",
                cost_usd=0.0,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
                timestamp=datetime.utcnow().isoformat(),
            )
            self.budget_manager.record_call(call)
            raise
    
    async def embed(
        self,
        texts: List[str],
        context: RoutingContext,
        **kwargs
    ) -> List[List[float]]:
        """嵌入调用"""
        decision = self.router.route(context)
        provider = await self._get_provider(decision.provider, decision.model)
        return await provider.embed(texts, **kwargs)
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        context: RoutingContext,
        top_n: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """重排序调用"""
        decision = self.router.route(context)
        provider = await self._get_provider(decision.provider, decision.model)
        return await provider.rerank(query, documents, top_n, **kwargs)
    
    async def _get_provider(self, provider_type: ProviderType, model: str) -> BaseProvider:
        """获取 Provider 实例（带缓存）"""
        cache_key = f"{provider_type.value}/{model}"
        
        if cache_key not in self.provider_cache:
            # 从 router 获取模型配置
            model_config = self.router.model_configs.get(model)
            if not model_config:
                raise ValueError(f"Model config not found: {model}")
            
            self.provider_cache[cache_key] = create_provider(provider_type, model_config)
        
        return self.provider_cache[cache_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        return {
            "call_stats": self.call_stats.copy(),
            "provider_cache_size": len(self.provider_cache),
        }
    
    def reset_session_budget(self, session_id: str):
        """重置会话预算（用于测试）"""
        self.budget_manager.initialize_session(session_id)
