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
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["https://app.salesboost.ai"]

    # Security
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ADMIN_USERNAME: Optional[str] = None
    ADMIN_PASSWORD_HASH: Optional[str] = None
    ADMIN_PASSWORD: Optional[str] = None
    ALLOW_INSECURE_ADMIN_PASSWORD: bool = False

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
    CONTEXT_SUMMARY_TRIGGER_RATIO: float = 0.8
    CONTEXT_LAYER_SYSTEM_BUDGET: int = 500
    CONTEXT_LAYER_MEMORY_BUDGET: int = 400
    CONTEXT_LAYER_STATE_BUDGET: int = 500
    CONTEXT_LAYER_HISTORY_BUDGET: int = 1500
    CONTEXT_LAYER_HISTORY_SUMMARY_BUDGET: int = 350
    CONTEXT_LAYER_KNOWLEDGE_BUDGET: int = 1500

    # Internal task routing (summaries, reflections, embeddings)
    LLM_MODEL_INTERNAL_TASK: str = "deepseek-chat"

    # Semantic cache
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.86
    SEMANTIC_CACHE_TTL_SECONDS: int = 3600
    SEMANTIC_CACHE_MAX_ENTRIES: int = 100

    # Observability
    TRACE_DB_PATH: str = "./monitoring/trace.db"
    TRACE_RETENTION_DAYS: int = 14
    METRICS_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True

    # Data retention
    DATA_RETENTION_DAYS: int = 90
    RETENTION_ENABLED: bool = True

    # LLM Settings by Agent Type
    COACH_TEMPERATURE: float = 0.3
    COACH_MAX_TOKENS: int = 800
    EVALUATOR_TEMPERATURE: float = 0.1
    EVALUATOR_MAX_TOKENS: int = 1200
    NPC_TEMPERATURE: float = 0.7
    NPC_MAX_TOKENS: int = 600
    RETRIEVER_TEMPERATURE: float = 0.1
    RETRIEVER_MAX_TOKENS: int = 400

    # RAG Thresholds
    RAG_SIMILARITY_THRESHOLD: float = 0.75
    RAG_TOP_K: int = 5
    RAG_CONFIDENCE_THRESHOLD: float = 0.6

    # Security & Compliance
    COMPLIANCE_INTERCEPT_WORDS: list[str] = ["refund", "complaint", "lawsuit", "scam"]
    SECURITY_INJECTION_PATTERNS: list[str] = [
        r"(ignore|disregard|forget)\s+(all\s+)?(instructions|rules|directions)",
        r"system\s+prompt",
        r"you\s+are\s+now\s+a"
    ]

    # Task Management
    SLOW_PATH_TIMEOUT_SECONDS: int = 30
    TRACE_ID_HEADER: str = "X-Trace-Id"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    """Return cached settings."""
    if settings.ENV_STATE == EnvironmentState.PRODUCTION:
        missing = []
        if not settings.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not settings.ADMIN_PASSWORD_HASH:
            missing.append("ADMIN_PASSWORD_HASH")
        if missing:
            raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")
    return settings
