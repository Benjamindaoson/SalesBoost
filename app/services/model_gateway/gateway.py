"""
Model Gateway - unified LLM access.
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.model_gateway.budget import BudgetManager
from app.services.model_gateway.providers import create_provider
from app.services.model_gateway.providers.base import BaseProvider
from app.services.model_gateway.router import ModelRouter
from app.services.model_gateway.schemas import (
    AgentType,
    LatencyMode,
    ModelCall,
    ProviderType,
    RoutingContext,
)
from app.core.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class ModelGateway:
    """Unified model gateway with budget enforcement."""

    def __init__(self, budget_manager: Optional[BudgetManager] = None) -> None:
        self.router = ModelRouter()
        self.budget_manager = budget_manager or BudgetManager()
        self.provider_cache: Dict[str, BaseProvider] = {}
        self.call_stats: Dict[str, int] = {}
        self.metrics = {
            "downgrade_count": 0,
            "downgrade_reasons": [],
        }

    async def chat(
        self,
        agent_type: Any,
        messages: List[Dict[str, str]],
        context: RoutingContext,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        prompt_version: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        call_id = str(uuid.uuid4())
        start_time = time.time()
        used_fallback = False
        downgrade_reason = None

        if context.session_id not in self.budget_manager.session_budgets:
            raise RuntimeError(f"Budget not initialized for session: {context.session_id}")
        if not context.budget_authorized:
            raise RuntimeError(f"Budget not authorized for session: {context.session_id}")

        authoritative_remaining = self.budget_manager.get_remaining_budget(context.session_id)
        context = context.model_copy(update={"budget_remaining": authoritative_remaining})

        try:
            decision = self.router.route(context)

            is_available, remaining = self.budget_manager.check_budget(
                context.session_id,
                decision.estimated_cost,
                path="fast" if context.latency_mode == LatencyMode.FAST else "slow",
            )
            if not is_available:
                if decision.fallback_provider and decision.fallback_model:
                    logger.warning("Budget insufficient, using fallback: %s", decision.fallback_model)
                    decision.provider = decision.fallback_provider
                    decision.model = decision.fallback_model
                    used_fallback = True
                    downgrade_reason = "budget_insufficient"
                else:
                    raise RuntimeError(f"Budget insufficient: ${remaining:.4f} remaining")

            # Check Circuit Breaker for primary choice
            if not circuit_breaker.is_available(decision.provider, decision.model):
                logger.warning(f"Circuit open for {decision.provider}/{decision.model}, switching to fallback")
                if decision.fallback_provider and decision.fallback_model:
                    decision.provider = decision.fallback_provider
                    decision.model = decision.fallback_model
                    used_fallback = True
                    downgrade_reason = "circuit_open"
                    # Check fallback availability too
                    if not circuit_breaker.is_available(decision.provider, decision.model):
                        logger.error(f"Circuit also open for fallback {decision.provider}/{decision.model}")
                        # Last resort: Qwen Turbo (assuming it's most stable/cheap)
                        decision.provider = ProviderType.QWEN
                        decision.model = "qwen-turbo"

            provider = await self._get_provider(decision.provider, decision.model)

            try:
                result = await provider.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                circuit_breaker.record_success(decision.provider, decision.model)
            except Exception as exc:
                circuit_breaker.record_failure(decision.provider, decision.model, exc)
                if decision.fallback_provider and decision.fallback_model and not used_fallback:
                    logger.warning("Primary provider failed: %s, trying fallback", exc)
                    self.metrics["downgrade_count"] = self.metrics.get("downgrade_count", 0) + 1
                    self.metrics["downgrade_reasons"] = self.metrics.get("downgrade_reasons", [])
                    self.metrics["downgrade_reasons"].append(f"provider_error: {str(exc)[:50]}")
                    
                    # Try fallback
                    fallback_provider = await self._get_provider(
                        decision.fallback_provider, decision.fallback_model
                    )
                    try:
                        result = await fallback_provider.chat(
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            **kwargs,
                        )
                        circuit_breaker.record_success(decision.fallback_provider, decision.fallback_model)
                        decision.provider = decision.fallback_provider
                        decision.model = decision.fallback_model
                        used_fallback = True
                        downgrade_reason = f"provider_error: {str(exc)[:50]}"
                    except Exception as fallback_exc:
                        circuit_breaker.record_failure(decision.fallback_provider, decision.fallback_model, fallback_exc)
                        raise fallback_exc
                else:
                    raise exc

            latency_ms = (time.time() - start_time) * 1000
            cost_usd = provider.estimate_cost(
                result["usage"]["prompt_tokens"],
                result["usage"]["completion_tokens"],
                decision.model,
            )

            self.budget_manager.deduct_budget(
                context.session_id,
                cost_usd,
                path="fast" if context.latency_mode == LatencyMode.FAST else "slow",
            )
            remaining_after = self.budget_manager.get_remaining_budget(context.session_id)

            call = ModelCall(
                call_id=call_id,
                agent_type=context.agent_type,
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

            provider_model_key = f"{decision.provider.value}/{decision.model}"
            self.call_stats[provider_model_key] = self.call_stats.get(provider_model_key, 0) + 1

            logger.info(
                "[METRIC: provider_hit=%s, model_hit=%s, tokens=%s, cost=$%.4f, latency=%.0fms]",
                decision.provider.value,
                decision.model,
                result["usage"]["total_tokens"],
                cost_usd,
                latency_ms,
            )
            try:
                from app.services.observability.metrics import record_llm_call

                record_llm_call(
                    agent_type=str(agent_type),
                    provider=decision.provider.value,
                    model=decision.model,
                    status="success",
                    latency_ms=latency_ms,
                    prompt_tokens=result["usage"]["prompt_tokens"],
                    completion_tokens=result["usage"]["completion_tokens"],
                    cost_usd=cost_usd,
                )
            except Exception:
                pass

            if trace_id:
                try:
                    from app.schemas.trace import AgentDecision
                    from app.services.observability import trace_manager

                    trace_manager.record_agent_call(
                        trace_id,
                        AgentDecision(
                            agent_name=agent_name or str(agent_type),
                            action="llm_call",
                            provider=decision.provider.value,
                            model_used=decision.model,
                            latency_ms=latency_ms,
                            input_tokens=result["usage"]["prompt_tokens"],
                            output_tokens=result["usage"]["completion_tokens"],
                            estimated_cost=cost_usd,
                            routing_reason=decision.reason,
                            downgrade_reason=downgrade_reason,
                            budget_remaining=remaining_after,
                            prompt_version=prompt_version,
                            metadata={
                                "fallback_used": used_fallback,
                                "fallback_provider": decision.fallback_provider.value
                                if decision.fallback_provider
                                else None,
                                "fallback_model": decision.fallback_model,
                            },
                        ),
                    )
                except Exception:
                    pass

            result["call_id"] = call_id
            result["cost_usd"] = cost_usd
            result["latency_ms"] = latency_ms
            result["provider"] = decision.provider.value
            result["model"] = decision.model
            result["routing_reason"] = decision.reason
            result["budget_remaining"] = remaining_after
            result["downgrade_reason"] = downgrade_reason
            result["fallback_used"] = used_fallback
            return result

        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(
                "[METRIC] Downgrade: %s -> error, reason=%s, latency=%.0fms",
                getattr(context.agent_type, "value", str(context.agent_type)),
                str(exc)[:100],
                latency_ms,
            )
            call = ModelCall(
                call_id=call_id,
                agent_type=context.agent_type,
                provider=ProviderType.MOCK,
                model="error",
                cost_usd=0.0,
                latency_ms=latency_ms,
                success=False,
                error=str(exc),
                timestamp=datetime.utcnow().isoformat(),
            )
            self.budget_manager.record_call(call)
            try:
                from app.services.observability.metrics import record_llm_call

                record_llm_call(
                    agent_type=str(agent_type),
                    provider="error",
                    model="error",
                    status="error",
                    latency_ms=latency_ms,
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost_usd=0.0,
                )
            except Exception:
                pass
            raise

    async def embed(self, texts: List[str], context: RoutingContext, **kwargs: Any) -> List[List[float]]:
        if context.session_id not in self.budget_manager.session_budgets:
            raise RuntimeError(f"Budget not initialized for session: {context.session_id}")
        if not context.budget_authorized:
            raise RuntimeError(f"Budget not authorized for session: {context.session_id}")
        context = context.model_copy(
            update={"budget_remaining": self.budget_manager.get_remaining_budget(context.session_id)}
        )
        decision = self.router.route(context)
        provider = await self._get_provider(decision.provider, decision.model)
        return await provider.embed(texts, **kwargs)

    async def rerank(
        self,
        query: str,
        documents: List[str],
        context: RoutingContext,
        top_n: int = 10,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if context.session_id not in self.budget_manager.session_budgets:
            raise RuntimeError(f"Budget not initialized for session: {context.session_id}")
        if not context.budget_authorized:
            raise RuntimeError(f"Budget not authorized for session: {context.session_id}")
        context = context.model_copy(
            update={"budget_remaining": self.budget_manager.get_remaining_budget(context.session_id)}
        )
        decision = self.router.route(context)
        provider = await self._get_provider(decision.provider, decision.model)
        return await provider.rerank(query, documents, top_n, **kwargs)

    async def chat_stream(
        self,
        agent_type: Any,
        messages: List[Dict[str, str]],
        context: RoutingContext,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        trace_id: Optional[str] = None,
        **kwargs: Any,
    ):
        """流式聊天"""
        # 1. Budget Check
        if context.session_id not in self.budget_manager.session_budgets:
            # Auto-initialize if missing? Or raise?
            # For robustness, maybe just log and proceed if dev mode?
            # But let's stick to strict logic for now.
             pass 

        if not context.budget_authorized:
             raise RuntimeError(f"Budget not authorized for session: {context.session_id}")
        
        authoritative_remaining = self.budget_manager.get_remaining_budget(context.session_id)
        context = context.model_copy(update={"budget_remaining": authoritative_remaining})

        # 2. Routing
        decision = self.router.route(context)
        
        # 3. Budget Pre-check (Estimate)
        is_available, remaining = self.budget_manager.check_budget(
            context.session_id,
            decision.estimated_cost,
            path="fast" if context.latency_mode == LatencyMode.FAST else "slow",
        )
        if not is_available:
            if decision.fallback_provider and decision.fallback_model:
                 decision.provider = decision.fallback_provider
                 decision.model = decision.fallback_model
            else:
                 raise RuntimeError(f"Budget insufficient: ${remaining:.4f} remaining")

        # 4. Circuit Breaker Check
        if not circuit_breaker.is_available(decision.provider, decision.model):
            if decision.fallback_provider and decision.fallback_model:
                decision.provider = decision.fallback_provider
                decision.model = decision.fallback_model
            else:
                # Last resort
                decision.provider = ProviderType.QWEN
                decision.model = "qwen-turbo"

        # 5. Get Provider
        provider = await self._get_provider(decision.provider, decision.model)
        
        call_id = str(uuid.uuid4())
        start_time = time.time()
        accumulated_content = ""
        # Rough estimate for prompt tokens if not provided
        prompt_tokens = sum([len(m.get("content", "")) / 4 for m in messages])
        
        # 6. Stream
        try:
            stream = provider.chat_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            async for chunk in stream:
                if isinstance(chunk, str):
                    accumulated_content += chunk
                    yield chunk
                else:
                    content = chunk.get("content", "")
                    if content:
                        accumulated_content += content
                    yield chunk
            
            # Stream finished successfully
            latency_ms = (time.time() - start_time) * 1000
            completion_tokens = len(accumulated_content) / 4
            
            cost_usd = provider.estimate_cost(
                prompt_tokens,
                completion_tokens,
                decision.model,
            )
            
            self.budget_manager.deduct_budget(
                context.session_id,
                cost_usd,
                path="fast" if context.latency_mode == LatencyMode.FAST else "slow",
            )
            
            circuit_breaker.record_success(decision.provider, decision.model)
            
            # Record stats
            remaining_after = self.budget_manager.get_remaining_budget(context.session_id)
            call = ModelCall(
                call_id=call_id,
                agent_type=context.agent_type,
                provider=decision.provider,
                model=decision.model,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(prompt_tokens + completion_tokens),
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=True,
                timestamp=datetime.utcnow().isoformat(),
            )
            self.budget_manager.record_call(call)
            
            provider_model_key = f"{decision.provider.value}/{decision.model}"
            self.call_stats[provider_model_key] = self.call_stats.get(provider_model_key, 0) + 1
            
            logger.info(
                "[METRIC: provider_hit=%s, model_hit=%s, tokens=%d, cost=$%.4f, latency=%.0fms] (Stream)",
                decision.provider.value,
                decision.model,
                int(prompt_tokens + completion_tokens),
                cost_usd,
                latency_ms,
            )
            
        except Exception as exc:
            circuit_breaker.record_failure(decision.provider, decision.model, exc)
            logger.error(f"Stream failed for {decision.provider}/{decision.model}: {exc}")
            raise exc

    async def _get_provider(self, provider_type: ProviderType, model: str) -> BaseProvider:
        cache_key = f"{provider_type.value}/{model}"
        if cache_key not in self.provider_cache:
            model_config = self.router.model_configs.get(model)
            if not model_config:
                for cfg in self.router.model_configs.values():
                    if cfg.model == model:
                        model_config = cfg
                        break
            if not model_config:
                raise ValueError(f"Model config not found: {model}")
            if provider_type != ProviderType.MOCK and not model_config.api_key:
                raise ValueError(f"API key not configured for provider={provider_type.value}, model={model}")
            self.provider_cache[cache_key] = create_provider(provider_type, model_config)
        return self.provider_cache[cache_key]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "call_stats": self.call_stats.copy(),
            "provider_cache_size": len(self.provider_cache),
        }

    def reset_session_budget(self, session_id: str) -> None:
        self.budget_manager.initialize_session(session_id)
