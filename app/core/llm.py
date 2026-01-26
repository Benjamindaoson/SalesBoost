"""
SalesBoost LLM Infrastructure
LangChain ChatOpenAI 工厂和实例管理
支持自定义 API Base URL (兼容 DeepSeek 等)
集成 LangSmith 监控：token 消耗、延迟、成本追踪
"""

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    raise ImportError(
        "langchain-openai is required for LLM functionality. "
        "Install with: pip install langchain-openai"
    )

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, AgentError

logger = logging.getLogger(__name__)

# OpenAI 模型定价 (USD per 1K tokens) - 2024 价格
MODEL_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}


@dataclass
class LLMUsageStats:
    """LLM 使用统计"""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    call_count: int = 0


class LangSmithCallbackHandler(BaseCallbackHandler):
    """
    LangSmith 兼容的回调处理器
    追踪 token 消耗、延迟时间、成本计算
    """

    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name
        self.stats = LLMUsageStats()
        self._start_time: Optional[float] = None

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """LLM 调用开始"""
        self._start_time = time.time()

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """LLM 调用结束，记录统计"""
        # 计算延迟
        if self._start_time:
            latency_ms = (time.time() - self._start_time) * 1000
            self.stats.total_latency_ms += latency_ms
            self._start_time = None

        # 提取 token 使用量
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)

            self.stats.prompt_tokens += prompt_tokens
            self.stats.completion_tokens += completion_tokens
            self.stats.total_tokens += prompt_tokens + completion_tokens

            # 计算成本
            pricing = MODEL_PRICING.get(self.model_name, MODEL_PRICING["gpt-4"])
            cost = (prompt_tokens / 1000 * pricing["input"]) + \
                   (completion_tokens / 1000 * pricing["output"])
            self.stats.total_cost_usd += cost

        self.stats.call_count += 1

        logger.debug(
            f"LLM call completed: model={self.model_name}, "
            f"tokens={self.stats.total_tokens}, cost=${self.stats.total_cost_usd:.4f}"
        )

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """LLM 调用错误"""
        logger.error(f"LLM error: {error}")
        self._start_time = None

    def get_stats(self) -> LLMUsageStats:
        """获取统计数据"""
        return self.stats

    def reset_stats(self) -> None:
        """重置统计"""
        self.stats = LLMUsageStats()


def _setup_langsmith_env(settings: Settings) -> bool:
    """
    配置 LangSmith 环境变量
    Returns: 是否成功启用 LangSmith
    """
    if not settings.LANGSMITH_API_KEY:
        logger.info("LangSmith API key not configured, tracing disabled")
        return False

    if not settings.LANGSMITH_TRACING_ENABLED:
        logger.info("LangSmith tracing disabled by config")
        return False

    # 设置 LangSmith 环境变量 (LangChain 自动读取)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT

    logger.info(f"LangSmith tracing enabled for project: {settings.LANGSMITH_PROJECT}")
    return True


class LLMFactory:
    """
    LLM 工厂类
    管理 ChatOpenAI 实例的创建和配置
    集成 LangSmith 监控
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化 LLM 工厂

        Args:
            settings: 配置对象，默认使用全局配置
        """
        self.settings = settings or get_settings()
        self._instances: Dict[str, ChatOpenAI] = {}
        self._callbacks: Dict[str, LangSmithCallbackHandler] = {}
        self._langsmith_enabled = _setup_langsmith_env(self.settings)

    async def get_npc_llm(self) -> ChatOpenAI:
        """
        获取 NPC 使用的 LLM 实例
        NPC 需要更高的 temperature 以增加对话多样性

        Returns:
            配置好的 ChatOpenAI 实例
        """
        return await self._get_or_create_llm(
            key="npc",
            temperature=0.7,  # NPC 需要多样性回复
            max_tokens=self.settings.OPENAI_MAX_TOKENS
        )

    async def get_coach_llm(self) -> ChatOpenAI:
        """
        获取教练使用的 LLM 实例
        教练需要较低的 temperature 以保证分析严谨性

        Returns:
            配置好的 ChatOpenAI 实例
        """
        return await self._get_or_create_llm(
            key="coach",
            temperature=0.2,  # 教练需要确定性分析
            max_tokens=self.settings.OPENAI_MAX_TOKENS
        )

    async def _get_or_create_llm(
        self,
        key: str,
        temperature: float,
        max_tokens: int
    ) -> ChatOpenAI:
        """
        获取或创建 LLM 实例

        Args:
            key: 实例缓存键
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            ChatOpenAI 实例
        """
        if key not in self._instances:
            # 验证配置
            if not self.settings.OPENAI_API_KEY:
                raise ConfigurationError(
                    "OPENAI_API_KEY is required for LLM functionality. "
                    "Please set it in your .env file."
                )

            # 创建回调处理器
            callback = LangSmithCallbackHandler(model_name=self.settings.OPENAI_MODEL)
            self._callbacks[key] = callback

            # 创建实例，注入回调
            self._instances[key] = ChatOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                base_url=self.settings.OPENAI_BASE_URL,
                model=self.settings.OPENAI_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30,  # 30秒超时
                max_retries=2,  # 最大重试次数
                callbacks=[callback],  # LangSmith 回调
            )

            logger.info(f"Created LLM instance: {key}, langsmith={self._langsmith_enabled}")

        return self._instances[key]

    def get_usage_stats(self, key: Optional[str] = None) -> Dict[str, LLMUsageStats]:
        """
        获取 LLM 使用统计

        Args:
            key: 指定实例键，None 返回所有

        Returns:
            使用统计字典
        """
        if key:
            if key in self._callbacks:
                return {key: self._callbacks[key].get_stats()}
            return {}
        return {k: cb.get_stats() for k, cb in self._callbacks.items()}

    def get_total_cost(self) -> float:
        """获取总成本 (USD)"""
        return sum(cb.stats.total_cost_usd for cb in self._callbacks.values())

    def get_total_tokens(self) -> int:
        """获取总 token 消耗"""
        return sum(cb.stats.total_tokens for cb in self._callbacks.values())

    async def test_connection(self) -> bool:
        """
        测试 LLM 连接是否正常

        Returns:
            连接是否正常
        """
        try:
            llm = await self.get_coach_llm()
            # 发送一个简单的测试消息
            response = await llm.ainvoke("Hello")
            return bool(response.content)
        except Exception as e:
            raise AgentError(f"LLM connection test failed: {e}")

    def clear_cache(self) -> None:
        """清除实例缓存和回调"""
        self._instances.clear()
        self._callbacks.clear()


# 全局 LLM 工厂实例
_llm_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """
    获取全局 LLM 工厂实例
    单例模式确保配置一致性

    Returns:
        LLMFactory 实例
    """
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = LLMFactory()
    return _llm_factory


@asynccontextmanager
async def llm_context():
    """
    LLM 上下文管理器
    用于管理 LLM 资源和异常处理
    """
    factory = get_llm_factory()
    try:
        yield factory
    except Exception as e:
        # 记录错误但不中断程序
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"LLM context error: {e}")
        raise
    finally:
        # 可选：清理资源
        pass


async def initialize_llm_system() -> None:
    """
    初始化 LLM 系统
    在应用启动时调用，验证配置和连接
    """
    factory = get_llm_factory()

    if not factory.settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured. Running in mock mode.")
        return

    try:
        # 测试连接
        await factory.test_connection()

        # 报告 LangSmith 状态
        langsmith_status = "enabled" if factory._langsmith_enabled else "disabled"
        logger.info(
            f"LLM system initialized successfully. "
            f"LangSmith: {langsmith_status}, "
            f"Project: {factory.settings.LANGSMITH_PROJECT}"
        )
    except Exception as e:
        logger.warning(f"LLM initialization failed: {e}. Falling back to mock mode.")


