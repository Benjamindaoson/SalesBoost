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
    CORS_ALLOW_HEADERS: list[str] = ["Authorization", "Content-Type", "Accept", "X-Trace-Id"]
    TRUST_PROXY_HEADERS: bool = False

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

    # Google Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # SiliconFlow (New)
    SILICONFLOW_API_KEY: Optional[str] = None  # SECURITY: Must be set via environment variable
    SILICONFLOW_MODEL: str = "deepseek-ai/DeepSeek-V3"
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"

    # WebSocket
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10
    WEBSOCKET_MANAGER_TYPE: str = "memory"  # memory|redis (use redis for horizontal scaling)

    # Session management
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_ACTIVE_SESSIONS: int = 100

    # FSM
    FSM_OPENING_TO_DISCOVERY_TURN_THRESHOLD: int = 2

    # Logging
    LOG_LEVEL: str = "INFO"

    # Feature flags
    AGENTIC_V3_ENABLED: bool = True
    ALLOW_LEGACY_COORDINATOR: bool = False
    BANDIT_ROUTING_ENABLED: bool = False
    BANDIT_REDIS_ENABLED: bool = False

    # Graph execution
    GRAPH_MAX_RETRIES: int = 3
    GRAPH_RETRY_DELAY: float = 1.0

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/salesboost.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Memory service
    MEMORY_STORAGE_BACKEND: str = "sqlite"  # redis|sqlite|local
    MEMORY_STORAGE_PATH: str = "./storage/memory"

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
    TOOL_CACHE_ENABLED: bool = True
    TOOL_CACHE_TOOLS: list[str] = ["knowledge_retriever", "profile_reader"]

    # Tool Retry Configuration
    TOOL_RETRY_ENABLED: bool = True
    TOOL_RETRY_MAX_ATTEMPTS: int = 3
    TOOL_RETRY_BASE_DELAY: float = 1.0

    # Tool Cache Enhancement
    TOOL_CACHE_LRU_ENABLED: bool = True
    TOOL_CACHE_ACCESS_TRACKING: bool = True

    # Tool Bandit Configuration
    TOOL_BANDIT_ENABLED: bool = False
    TOOL_BANDIT_EPSILON: float = 0.1
    TOOL_BANDIT_REDIS_KEY: str = "tool:bandit:state"

    # Tool Rate Limiting
    TOOL_RATE_LIMIT_ENABLED: bool = True

    # Tool Parallel Execution
    TOOL_PARALLEL_ENABLED: bool = True
    TOOL_PARALLEL_MAX_CONCURRENT: int = 5

    # Observability
    TRACE_DB_PATH: str = "./monitoring/trace.db"
    TRACE_RETENTION_DAYS: int = 14
    METRICS_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True

    # Model lifecycle governance
    LIFECYCLE_JOB_INTERVAL_SECONDS: float = 60.0
    LIFECYCLE_ANOMALY_MIN_DROP: float = 2.0

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
    # RAG Configuration
    RAG_SIMILARITY_THRESHOLD: float = 0.75
    RAG_TOP_K: int = 5
    RAG_CONFIDENCE_THRESHOLD: float = 0.6
    RAG_HYBRID_ENABLED: bool = True

    # Embedding Model Configuration
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"  # Upgraded from all-MiniLM-L6-v2
    EMBEDDING_DIMENSION: int = 384  # Will be auto-detected from model
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DEVICE: str = "cpu"  # or "cuda" for GPU
    EMBEDDING_NORMALIZE: bool = True

    # Alternative models (can be switched via env var)
    # - "paraphrase-multilingual-MiniLM-L12-v2": 384 dim, multilingual
    # - "shibing624/text2vec-base-chinese": 768 dim, Chinese optimized
    # - "BAAI/bge-m3": 1024 dim, best quality
    # - "text-embedding-3-small": 1536 dim, OpenAI (requires API key)

    # BM25 Configuration
    BM25_K1: float = 1.5  # Term frequency saturation
    BM25_B: float = 0.75  # Length normalization
    BM25_USE_JIEBA: bool = True  # Chinese word segmentation

    # Vector Store Configuration
    VECTOR_STORE_URL: Optional[str] = None  # Qdrant URL (None = local mode)
    VECTOR_STORE_API_KEY: Optional[str] = None
    VECTOR_STORE_COLLECTION: str = "sales_knowledge"
    VECTOR_STORE_DISTANCE: str = "Cosine"

    # BGE-Reranker Configuration (Week 2)
    BGE_RERANKER_ENABLED: bool = True
    BGE_RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    BGE_RERANKER_TOP_K: int = 5
    BGE_RERANKER_BATCH_SIZE: int = 32

    # Small-to-Big Chunking Configuration (Level 2 Upgrade)
    CHUNKING_STRATEGY: str = "small_to_big"  # "small_to_big" or "legacy"
    CHUNKING_PARENT_SIZE: int = 1024  # Parent chunk size (512-1024 tokens)
    CHUNKING_CHILD_SIZE: int = 256  # Child chunk size (128 tokens)
    CHUNKING_PARENT_OVERLAP: int = 100  # Overlap between parent chunks
    CHUNKING_CHILD_OVERLAP: int = 50  # Overlap between child chunks

    # Long-Term Memory Configuration (Week 3)
    LONG_TERM_MEMORY_ENABLED: bool = True
    LONG_TERM_MEMORY_LOOKBACK_DAYS: int = 30
    LONG_TERM_MEMORY_MAX_RESULTS: int = 5

    # Self-Correction Configuration (Week 3)
    SELF_CORRECTION_ENABLED: bool = True
    SELF_CORRECTION_MAX_ATTEMPTS: int = 2
    SELF_CORRECTION_CONFIDENCE_THRESHOLD: float = 0.7

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
        extra = "ignore"  # Ignore extra fields from .env


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
