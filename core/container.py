"""
Dependency Injection Container - 依赖注入容器 (简化版)
提升模块化、可测试性和配置管理
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.database import get_db_session
from core.redis import get_redis_client
from app.cognitive.brain.state.fsm_engine import FSMEngine


class Container:
    """主依赖注入容器 - 简化版"""

    def __init__(self):
        self._config = None
        self._redis_client = None
        self._fsm_engine = None

    def get_config(self) -> Settings:
        """获取配置"""
        try:
            from core.config import get_settings

            return get_settings()
        except Exception:
            # 默认配置
            return Settings()

    def get_redis(self):
        """获取Redis客户端"""
        try:
            return get_redis_client()
        except Exception:
            return None

    def get_fsm_engine(self) -> Optional[FSMEngine]:
        """获取FSM引擎"""
        try:
            return FSMEngine()
        except Exception:
            return None


class ProductionContainer(Container):
    """生产环境容器"""

    pass


class DevelopmentContainer(Container):
    """开发环境容器"""

    pass


class TestContainer(Container):
    """测试环境容器"""

    def __init__(self):
        super().__init__()
        self._mock_llm_router = MockLLMRouter()

    def get_llm_router(self):
        """返回Mock LLM Router"""
        return self._mock_llm_router


# Mock 实现 - 用于测试
class MockLLMRouter:
    """Mock LLM Router - 用于测试"""

    def __init__(self):
        self.call_count = {}

    def get_llm_instance(self, agent_type: str):
        """返回 Mock LLM 实例"""
        self.call_count[agent_type] = self.call_count.get(agent_type, 0) + 1

        # 简化的Mock实现
        class MockLLM:
            def __init__(self, response_text: str):
                self.response_text = response_text

            async def ainvoke(self, prompt: str, **kwargs):
                return type("MockResponse", (), {"content": self.response_text})()

            def invoke(self, prompt: str, **kwargs):
                return type("MockResponse", (), {"content": self.response_text})()

        # 针对不同智能体类型返回不同的模拟响应
        if agent_type == "npc":
            return MockLLM("这是NPC的模拟回复")
        elif agent_type == "coach":
            return MockLLM("这是教练的模拟建议")
        elif agent_type == "evaluator":
            return MockLLM('{"score": 8.5, "feedback": "表现良好"}')
        else:
            return MockLLM("这是通用模拟回复")


# 全局容器实例
_container: Optional[Container] = None


def get_container() -> Container:
    """获取当前容器实例"""
    global _container
    if _container is None:
        try:
            from core.config import get_settings

            settings = get_settings()

            if settings.ENV_STATE == "testing":
                _container = TestContainer()
            elif settings.ENV_STATE == "production":
                _container = ProductionContainer()
            else:
                _container = DevelopmentContainer()
        except Exception:
            # 默认使用开发容器
            _container = DevelopmentContainer()

    return _container


def init_container(env_state: str = "development") -> Container:
    """初始化容器"""
    global _container

    if env_state == "testing":
        _container = TestContainer()
    elif env_state == "production":
        _container = ProductionContainer()
    else:
        _container = DevelopmentContainer()

    return _container


# FastAPI 依赖注入辅助函数
async def get_db_session_from_container() -> AsyncSession:
    """从容器获取数据库会话"""
    # 直接调用，不通过容器
    return await get_db_session().__anext__()


def get_fsm_engine_from_container() -> Optional[FSMEngine]:
    """从容器获取 FSM 引擎"""
    container = get_container()
    return container.get_fsm_engine()


# 导出主要类
__all__ = [
    "Container",
    "ProductionContainer",
    "DevelopmentContainer",
    "TestContainer",
    "get_container",
    "init_container",
    "get_db_session_from_container",
    "get_fsm_engine_from_container",
]
