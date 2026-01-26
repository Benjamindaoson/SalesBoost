"""
LLM Router - 适配器层 (Adapter over ModelGateway)

【重要】此模块是 model_gateway 的适配器，用于 V2 兼容
新代码应直接使用 app.services.model_gateway

职责：
- 复用 model_gateway 的配置和路由逻辑
- 返回 LangChain LLM 对象（V2 agents 兼容）
- 统一配置入口（所有配置在 model_gateway/router.py）
"""

import logging
import warnings
from typing import Optional, Dict, Any
from enum import Enum

from langchain_openai import ChatOpenAI

try:
    from langchain_community.chat_models import ChatTongyi, ChatZhipuAI
except ImportError:
    try:
        from langchain_community.chat_models.tongyi import ChatTongyi
    except ImportError:
        ChatTongyi = None
    try:
        from langchain_community.chat_models.zhipuai import ChatZhipuAI
    except ImportError:
        ChatZhipuAI = None

from app.core.config import get_settings
from app.services.model_gateway.router import ModelRouter
from app.services.model_gateway.schemas import ProviderType, AgentType as GatewayAgentType

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent 类型枚举 (V2 兼容)"""
    INTENT_GATE = "intent_gate"
    NPC = "npc"
    COACH = "coach"
    EVALUATOR = "evaluator"
    RAG = "rag"
    COMPLIANCE = "compliance"


# Agent 默认 temperature 配置
AGENT_TEMPERATURE = {
    AgentType.INTENT_GATE: 0.1,
    AgentType.NPC: 0.7,
    AgentType.COACH: 0.2,
    AgentType.EVALUATOR: 0.1,
    AgentType.RAG: 0.2,
    AgentType.COMPLIANCE: 0.0,
}

# V2 AgentType -> V3 GatewayAgentType 映射
_AGENT_TYPE_MAPPING = {
    AgentType.INTENT_GATE: GatewayAgentType.INTENT_GATE,
    AgentType.NPC: GatewayAgentType.NPC,
    AgentType.COACH: GatewayAgentType.COACH,
    AgentType.EVALUATOR: GatewayAgentType.EVALUATOR,
    AgentType.RAG: GatewayAgentType.RAG,
    AgentType.COMPLIANCE: GatewayAgentType.COMPLIANCE,
}


class LLMRouter:
    """
    LLM 路由器 - ModelGateway 适配器

    【废弃警告】此类仅用于 V2 兼容，新代码请使用 model_gateway
    """

    def __init__(self):
        self._settings = get_settings()
        self._instances: Dict[str, Any] = {}

        # 复用 model_gateway 的路由器（统一配置源）
        self._model_router = ModelRouter()

        logger.info("[LLMRouter] Initialized (adapter mode, config from model_gateway)")

    def get_model_for_agent(self, agent_type: str) -> str:
        """获取指定 Agent 应使用的模型名称"""
        if not self._settings.LLM_ROUTER_ENABLED:
            return self._settings.OPENAI_MODEL

        try:
            agent_enum = AgentType(agent_type.lower())
            gateway_agent = _AGENT_TYPE_MAPPING.get(agent_enum)
            if gateway_agent:
                # 复用 model_gateway 的模型选择逻辑
                from app.services.model_gateway.schemas import LatencyMode
                return self._model_router._get_default_model(gateway_agent, LatencyMode.SLOW)
        except (ValueError, KeyError):
            pass

        logger.warning(f"[LLMRouter] Unknown agent type: {agent_type}, using default")
        return self._settings.OPENAI_MODEL

    def get_llm_instance(
        self,
        agent_type: str,
        temperature: Optional[float] = None,
        max_tokens: int = 2000,
    ) -> Any:
        """
        获取指定 Agent 的 LLM 实例

        返回 LangChain ChatOpenAI/ChatTongyi/ChatZhipuAI 实例
        """
        model_name = self.get_model_for_agent(agent_type)
        provider = self._model_router._infer_provider(model_name)
        api_key, base_url = self._model_router._get_provider_credentials(provider)

        if not api_key:
            logger.warning(
                f"[LLMRouter] {provider.value} API key not configured for {agent_type}, "
                f"falling back to available provider"
            )
            return self._get_fallback_instance(temperature or 0.2, max_tokens)

        # 确定 temperature
        if temperature is None:
            try:
                agent_enum = AgentType(agent_type.lower())
                temperature = AGENT_TEMPERATURE.get(agent_enum, 0.2)
            except ValueError:
                temperature = 0.2

        cache_key = f"{agent_type}:{model_name}:{temperature}"

        if cache_key not in self._instances:
            try:
                self._instances[cache_key] = self._create_llm_instance(
                    provider=provider,
                    model_name=model_name,
                    api_key=api_key,
                    base_url=base_url,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                logger.info(
                    f"[LLMRouter] {agent_type} -> {model_name} "
                    f"(provider={provider.value}, temp={temperature})"
                )
            except Exception as e:
                logger.error(f"[LLMRouter] Failed to create LLM for {agent_type}: {e}")
                return self._get_fallback_instance(temperature, max_tokens)

        return self._instances[cache_key]

    def _create_llm_instance(
        self,
        provider: ProviderType,
        model_name: str,
        api_key: str,
        base_url: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> Any:
        """创建 LangChain LLM 实例"""
        if provider == ProviderType.QWEN:
            qwen_llm = self._create_qwen_llm(model_name, api_key, temperature, max_tokens)
            if qwen_llm is not None:
                return qwen_llm
        elif provider == ProviderType.ZHIPU:
            zhipu_llm = self._create_zhipu_llm(model_name, api_key, temperature, max_tokens)
            if zhipu_llm is not None:
                return zhipu_llm

        # 默认使用 OpenAI 兼容接口
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=120,
            max_retries=3,
        )

    def _create_qwen_llm(
        self,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
    ) -> Optional[Any]:
        if ChatTongyi is None:
            logger.warning("[LLMRouter] ChatTongyi not available, using ChatOpenAI for Qwen.")
            return None
        try:
            return ChatTongyi(
                model=model_name,
                dashscope_api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.warning("[LLMRouter] ChatTongyi init failed, using ChatOpenAI: %s", exc)
            return None

    def _create_zhipu_llm(
        self,
        model_name: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
    ) -> Optional[Any]:
        if ChatZhipuAI is None:
            logger.warning("[LLMRouter] ChatZhipuAI not available, using ChatOpenAI for GLM.")
            return None
        try:
            return ChatZhipuAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.warning("[LLMRouter] ChatZhipuAI init failed, using ChatOpenAI: %s", exc)
            return None

    def _get_fallback_instance(
        self,
        temperature: float,
        max_tokens: int,
    ) -> Any:
        """获取降级模型实例"""
        fallback_model = self._settings.LLM_FALLBACK_MODEL
        provider = self._model_router._infer_provider(fallback_model)
        api_key, base_url = self._model_router._get_provider_credentials(provider)

        if not api_key:
            # 尝试其他 Provider
            for try_provider in [ProviderType.QWEN, ProviderType.OPENAI]:
                fb_key, fb_url = self._model_router._get_provider_credentials(try_provider)
                if fb_key:
                    api_key, base_url = fb_key, fb_url
                    fallback_model = "qwen-turbo" if try_provider == ProviderType.QWEN else "gpt-3.5-turbo"
                    provider = try_provider
                    break

        if not api_key:
            raise RuntimeError(
                "[LLMRouter] No API key configured for any provider. "
                "Please set DASHSCOPE_API_KEY, QWEN_API_KEY, ZHIPU_API_KEY, or OPENAI_API_KEY."
            )

        fallback_key = f"fallback:{fallback_model}:{temperature}"

        if fallback_key not in self._instances:
            self._instances[fallback_key] = self._create_llm_instance(
                provider=provider,
                model_name=fallback_model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.warning(f"[LLMRouter] Using fallback: {fallback_model} (provider={provider.value})")

        return self._instances[fallback_key]

    def clear_cache(self) -> None:
        """清除实例缓存"""
        self._instances.clear()
        logger.info("[LLMRouter] Cache cleared")


# 全局实例
_llm_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """获取 LLM 路由器实例"""
    global _llm_router
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router


def reset_llm_router() -> None:
    """重置 LLM 路由器（用于测试）"""
    global _llm_router
    if _llm_router:
        _llm_router.clear_cache()
    _llm_router = None
