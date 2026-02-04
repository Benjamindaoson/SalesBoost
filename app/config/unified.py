"""
Unified Configuration System

Consolidates all configuration into a single, well-organized Settings class.

Features:
- Grouped settings by domain
- Type validation with Pydantic
- Environment variable support
- Secrets manager integration
- Configuration validation

Usage:
    from app.config.unified import get_unified_settings

    settings = get_unified_settings()
    print(settings.llm.openai_api_key)
    print(settings.websocket.manager_type)
"""

import logging
from typing import Optional, List
from enum import Enum

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, field_validator
except ImportError:
    from pydantic import BaseSettings

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class EnvironmentState(str, Enum):
    """Runtime environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class WebSocketManagerType(str, Enum):
    """WebSocket manager type"""
    MEMORY = "memory"  # In-memory (single server)
    REDIS = "redis"    # Redis-based (horizontal scaling)


class CoordinatorEngine(str, Enum):
    """Coordinator engine type"""
    DYNAMIC_WORKFLOW = "dynamic_workflow"


# ==================== Settings Groups ====================

class CoreSettings(BaseSettings):
    """Core application settings"""
    project_name: str = "SalesBoost"
    version: str = "2.0.0"
    description: str = "AI-powered sales coaching platform"
    env_state: EnvironmentState = EnvironmentState.DEVELOPMENT
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_prefix = ""


class ServerSettings(BaseSettings):
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False

    class Config:
        env_prefix = "SERVER_"


class SecuritySettings(BaseSettings):
    """Security configuration"""
    secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_username: Optional[str] = None
    admin_password_hash: Optional[str] = None
    allow_insecure_admin_password: bool = False

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    cors_allow_headers: List[str] = ["Authorization", "Content-Type", "Accept"]
    trust_proxy_headers: bool = False

    class Config:
        env_prefix = ""


class LLMSettings(BaseSettings):
    """LLM provider configuration"""
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_base_url: Optional[str] = None
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7

    # Google Gemini
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

    # SiliconFlow (DeepSeek)
    siliconflow_api_key: Optional[str] = None
    siliconflow_model: str = "deepseek-ai/DeepSeek-V3"
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    # vLLM (for OCR)
    vllm_ocr_url: str = "http://localhost:8000"

    class Config:
        env_prefix = ""


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    database_url: str = "sqlite+aiosqlite:///./storage/salesboost.db"
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_recycle: int = 3600

    class Config:
        env_prefix = ""


class RedisSettings(BaseSettings):
    """Redis configuration"""
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    class Config:
        env_prefix = ""


class WebSocketSettings(BaseSettings):
    """WebSocket configuration"""
    ping_interval: int = 30
    ping_timeout: int = 10
    manager_type: WebSocketManagerType = WebSocketManagerType.MEMORY
    max_active_sessions: int = 100

    class Config:
        env_prefix = "WEBSOCKET_"


class CoordinatorSettings(BaseSettings):
    """Coordinator configuration"""
    engine: CoordinatorEngine = CoordinatorEngine.DYNAMIC_WORKFLOW
    allow_legacy_coordinator: bool = False
    bandit_routing_enabled: bool = False
    bandit_redis_enabled: bool = False
    graph_max_retries: int = 3
    graph_retry_delay: float = 1.0

    class Config:
        env_prefix = ""


class RAGSettings(BaseSettings):
    """RAG configuration"""
    # Vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 768

    # Retrieval
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.75
    rag_hybrid_enabled: bool = True

    # Reranker
    bge_reranker_enabled: bool = True
    bge_reranker_model: str = "BAAI/bge-reranker-base"
    bge_reranker_top_k: int = 5

    class Config:
        env_prefix = ""


class ContextSettings(BaseSettings):
    """Context management configuration"""
    context_max_tokens: int = 4000
    context_summary_enabled: bool = True
    context_summary_model: str = "qwen-turbo"
    context_summary_trigger_ratio: float = 0.8

    # Layer budgets
    context_layer_system_budget: int = 500
    context_layer_memory_budget: int = 400
    context_layer_state_budget: int = 500
    context_layer_history_budget: int = 1500

    class Config:
        env_prefix = ""


class ToolSettings(BaseSettings):
    """Tool execution configuration"""
    tool_retry_enabled: bool = True
    tool_retry_max_attempts: int = 3
    tool_parallel_enabled: bool = True
    tool_parallel_max_concurrent: int = 5
    tool_cache_enabled: bool = True
    tool_rate_limit_enabled: bool = True

    class Config:
        env_prefix = ""


class ObservabilitySettings(BaseSettings):
    """Observability configuration"""
    prometheus_enabled: bool = True
    tracing_enabled: bool = False
    jaeger_endpoint: Optional[str] = None
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"
    sentry_traces_sample_rate: float = 0.1

    class Config:
        env_prefix = ""


class FeatureFlagSettings(BaseSettings):
    """Feature flags"""
    agentic_v3_enabled: bool = True
    semantic_cache_enabled: bool = True
    long_term_memory_enabled: bool = True
    self_correction_enabled: bool = True

    class Config:
        env_prefix = ""


# ==================== Unified Settings ====================

class UnifiedSettings(BaseSettings):
    """
    Unified configuration for SalesBoost

    All settings are grouped by domain for better organization.
    """

    # Core
    core: CoreSettings = CoreSettings()
    server: ServerSettings = ServerSettings()
    security: SecuritySettings = SecuritySettings()

    # Infrastructure
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    websocket: WebSocketSettings = WebSocketSettings()

    # AI/ML
    llm: LLMSettings = LLMSettings()
    rag: RAGSettings = RAGSettings()
    context: ContextSettings = ContextSettings()

    # Application
    coordinator: CoordinatorSettings = CoordinatorSettings()
    tools: ToolSettings = ToolSettings()

    # Observability
    observability: ObservabilitySettings = ObservabilitySettings()
    features: FeatureFlagSettings = FeatureFlagSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def validate_production(self) -> List[str]:
        """
        Validate production configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if self.core.env_state == EnvironmentState.PRODUCTION:
            # Check required secrets
            if not self.security.secret_key:
                errors.append("SECRET_KEY is required in production")

            if not self.llm.openai_api_key and not self.llm.siliconflow_api_key:
                errors.append("At least one LLM API key is required")

            # Check Redis for horizontal scaling
            if self.websocket.manager_type == WebSocketManagerType.REDIS:
                if "localhost" in self.redis.redis_url:
                    errors.append("Redis URL should not use localhost in production")

            # Check database
            if "sqlite" in self.database.database_url:
                errors.append("SQLite is not recommended for production")

        return errors


# ==================== Factory Functions ====================

_unified_settings: Optional[UnifiedSettings] = None


def get_unified_settings(force_reload: bool = False) -> UnifiedSettings:
    """
    Get unified settings instance (singleton)

    Args:
        force_reload: Force reload from environment

    Returns:
        UnifiedSettings instance
    """
    global _unified_settings

    if _unified_settings is None or force_reload:
        _unified_settings = UnifiedSettings()

        # Validate production config
        if _unified_settings.core.env_state == EnvironmentState.PRODUCTION:
            errors = _unified_settings.validate_production()
            if errors:
                logger.error("Production configuration validation failed:")
                for error in errors:
                    logger.error(f"  - {error}")
                raise ValueError("Invalid production configuration")

        logger.info(
            f"[UnifiedSettings] Loaded configuration for "
            f"{_unified_settings.core.env_state.value} environment"
        )

    return _unified_settings


def reload_settings():
    """Reload settings from environment"""
    global _unified_settings
    _unified_settings = None
    return get_unified_settings()
