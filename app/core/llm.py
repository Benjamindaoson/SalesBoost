"""
SalesBoost LLM Infrastructure
LangChain ChatOpenAI 工厂和实例管理
支持自定义 API Base URL (兼容 DeepSeek 等)
"""

import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    # 如果没有安装 langchain-openai，提供有用的错误信息
    raise ImportError(
        "langchain-openai is required for LLM functionality. "
        "Install with: pip install langchain-openai"
    )

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, AgentError


class LLMFactory:
    """
    LLM 工厂类
    管理 ChatOpenAI 实例的创建和配置
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        初始化 LLM 工厂

        Args:
            settings: 配置对象，默认使用全局配置
        """
        self.settings = settings or get_settings()
        self._instances: Dict[str, ChatOpenAI] = {}

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

            # 创建实例
            self._instances[key] = ChatOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                base_url=self.settings.OPENAI_BASE_URL,
                model=self.settings.OPENAI_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30,  # 30秒超时
                max_retries=2,  # 最大重试次数
            )

        return self._instances[key]

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
        """清除实例缓存"""
        self._instances.clear()


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
    import logging
    logger = logging.getLogger(__name__)
    
    factory = get_llm_factory()

    if not factory.settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured. Running in mock mode.")
        return

    try:
        # 测试连接
        await factory.test_connection()
        logger.info("LLM system initialized successfully")
    except Exception as e:
        logger.warning(f"LLM initialization failed: {e}. Falling back to mock mode.")


