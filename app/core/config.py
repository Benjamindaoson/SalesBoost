"""
SalesBoost Configuration Management (基础设施层)

核心职责：
- 统一管理所有配置项，避免硬编码
- 支持环境变量和 .env 文件配置
- 提供类型安全的配置访问
- 遵循 12-Factor App 配置外部化原则

配置分类：
├── 项目信息: PROJECT_NAME, VERSION, DESCRIPTION
├── 环境控制: ENV_STATE, DEBUG
├── 服务器设置: HOST, PORT, CORS_ORIGINS
├── LLM 配置: OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL
├── 会话管理: SESSION_TIMEOUT_MINUTES, MAX_ACTIVE_SESSIONS
├── FSM 规则: OPENING_TO_DISCOVERY_TURN_THRESHOLD
└── 性能调优: WEBSOCKET_PING_INTERVAL, GRAPH_MAX_RETRIES

使用示例:
    from app.core.config import get_settings
    settings = get_settings()
    model_name = settings.OPENAI_MODEL
"""

from typing import Optional
from enum import Enum

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class EnvironmentState(str, Enum):
    """环境状态枚举"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """
    应用配置类
    所有配置项都通过环境变量或 .env 文件设置
    """

    # 项目基本信息
    PROJECT_NAME: str = "SalesBoost"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "基于 Multi-Agent 的销售能力复制平台"

    # 环境配置
    ENV_STATE: EnvironmentState = EnvironmentState.DEVELOPMENT
    DEBUG: bool = True

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]  # 生产环境请设置具体域名

    # OpenAI 配置 (目前可选，用于未来替换 Mock)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7

    # WebSocket 配置
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10

    # 会话管理
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_ACTIVE_SESSIONS: int = 100

    # FSM 配置
    FSM_OPENING_TO_DISCOVERY_TURN_THRESHOLD: int = 2  # Opening -> Discovery 需要的对话轮数

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # LangGraph 配置
    GRAPH_MAX_RETRIES: int = 3
    GRAPH_RETRY_DELAY: float = 1.0
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./salesboost.db"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        """Pydantic 配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

        # 环境变量前缀 (可选)
        # env_prefix = "SALESBOOST_"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """
    获取配置实例
    用于依赖注入
    """
    return settings
