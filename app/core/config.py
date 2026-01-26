"""
SalesBoost configuration management.
"""
from enum import Enum
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback for older pydantic installs
    from pydantic import BaseSettings


class EnvironmentState(str, Enum):
    """Runtime environment."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """Application settings loaded from env or .env."""

    # Project metadata
    PROJECT_NAME: str = "SalesBoost"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Multi-agent sales coaching platform."

    # Environment
    ENV_STATE: EnvironmentState = EnvironmentState.DEVELOPMENT
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # OpenAI (optional)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7

    # WebSocket
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10

    # Session management
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_ACTIVE_SESSIONS: int = 100

    # FSM
    FSM_OPENING_TO_DISCOVERY_TURN_THRESHOLD: int = 2

    # Logging
    LOG_LEVEL: str = "INFO"

    # Feature flags
    AGENTIC_V3_ENABLED: bool = True

    # Graph execution
    GRAPH_MAX_RETRIES: int = 3
    GRAPH_RETRY_DELAY: float = 1.0

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./salesboost.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Memory service
    MEMORY_STORAGE_BACKEND: str = "sqlite"  # redis|sqlite|local
    MEMORY_STORAGE_PATH: str = "./data/memory"

    # Context summarization
    CONTEXT_MAX_TOKENS: int = 4000
    CONTEXT_SUMMARY_ENABLED: bool = True
    CONTEXT_SUMMARY_MODEL: str = "qwen-turbo"

    # Semantic cache
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.86
    SEMANTIC_CACHE_TTL_SECONDS: int = 3600
    SEMANTIC_CACHE_MAX_ENTRIES: int = 100

    # Observability
    TRACE_DB_PATH: str = "./monitoring/trace.db"
    TRACE_RETENTION_DAYS: int = 14

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    """Return cached settings."""

    return settings
