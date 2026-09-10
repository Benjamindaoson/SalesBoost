from __future__ import annotations

import os
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "SalesAgent"
    app_version: str = "3.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "salesagent"
    postgres_password: str = "salesagent_secret"
    postgres_db: str = "salesagent"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 0
    working_memory_ttl_seconds: int = 7200  # 2 hours

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── MinIO ─────────────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin_secret"
    minio_secure: bool = False
    minio_knowledge_bucket: str = "knowledge-base"

    # ── LLM API Keys ──────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # Uppercase aliases for compatibility
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Sync lowercase and uppercase versions
        if self.anthropic_api_key and not self.ANTHROPIC_API_KEY:
            self.ANTHROPIC_API_KEY = self.anthropic_api_key
        if self.openai_api_key and not self.OPENAI_API_KEY:
            self.OPENAI_API_KEY = self.openai_api_key
        if self.deepseek_api_key and not self.DEEPSEEK_API_KEY:
            self.DEEPSEEK_API_KEY = self.deepseek_api_key
        if self.deepseek_base_url and not self.DEEPSEEK_BASE_URL:
            self.DEEPSEEK_BASE_URL = self.deepseek_base_url

    # ── Model Configuration ───────────────────────────────────────────────────
    mock_llm: bool = Field(default=True, description="Use mock LLM for testing without API keys")
    lite_mode: bool = Field(default=False, description="Enable Lite Mode (3-node DAG) for B2C")
    tiered_routing_enabled: bool = Field(default=True, description="Dynamically switch to Lite Mode based on value")
    degradation_urgency_threshold: float = Field(default=0.4, description="Standard users with urgency < this use Lite Mode")
    vip_customers: list[str] = Field(default_factory=list, description="List of IDs that always use Cold Path")
    primary_reasoning_model: str = "claude-sonnet-4-20250514"
    primary_response_model: str = "claude-sonnet-4-20250514"
    deepseek_model: str = "deepseek-chat"
    guard_model: str = "gpt-4o-mini"
    critic_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ── Shadow Mode ───────────────────────────────────────────────────────────
    shadow_mode_enabled: bool = True
    shadow_mode_ratio: float = 0.10  # 10% of traffic
    shadow_model: str = "gpt-4o-mini"

    # ── Gateway ───────────────────────────────────────────────────────────────
    gateway_timeout_seconds: float = 30.0
    gateway_max_retries: int = 3
    gateway_retry_backoff: float = 0.5

    # ── Reasoning Chain ───────────────────────────────────────────────────────
    reasoning_cache_enabled: bool = True
    reasoning_cache_similarity_threshold: float = 0.92
    reasoning_cache_ttl_seconds: int = 3600

    # ── Knowledge Retrieval ───────────────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_chunk_size: int = 512
    retrieval_chunk_overlap: int = 50
    hot_path_threshold: float = 0.85

    # ── Guard ─────────────────────────────────────────────────────────────────
    guard_enabled: bool = True
    guard_sentence_buffer_max_tokens: int = 100

    memory_importance_threshold: float = 0.2

    # ── Typing Simulation (PRD NFR) ──────────────────────────────────────────
    typing_sim_delay_min: float = 15.0
    typing_sim_delay_max: float = 90.0

    # ── APO Engine ────────────────────────────────────────────────────────────
    apo_cycle_min_samples: int = 100
    apo_variant_count: int = 5
    apo_ab_traffic_weight: float = 0.10

    # ── Telemetry ────────────────────────────────────────────────────────────
    otel_endpoint: str = ""
    otlp_endpoint: str = ""
    trace_sampling_rate: float = 1.0
    langsmith_api_key: str = ""
    langsmith_project: str = "salesagent-v3"

    # ── Sentry Error Tracking ────────────────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    # ── WeChat Personal ──────────────────────────────────────────────────────
    wechat_personal_enabled: bool = True
    wechat_personal_auto_login: bool = True
    wechat_personal_qr_callback_url: str = ""
    wechat_personal_hot_reload: bool = True
    wechat_personal_session_file: str = ".wechat_session.pkl"

    # ── WeChat Work (Enterprise WeChat) ──────────────────────────────────────
    wechat_work_enabled: bool = False
    wechat_work_corp_id: str = ""
    wechat_work_agent_id: str = ""
    wechat_work_secret: str = ""
    wechat_work_token: str = ""
    wechat_work_encoding_aes_key: str = ""
    wechat_work_webhook_url: str = ""

    # ── Security ──────────────────────────────────────────────────────────────
    encryption_key: str = ""  # Fernet key, generate with: Fernet.generate_key()
    enable_rls: bool = True
    pii_fields: list[str] = ["name", "phone", "id_card", "email"]

    # ── JWT Authentication ────────────────────────────────────────────────────
    jwt_secret_key: str = Field(
        default="your-secret-key-change-in-production-use-openssl-rand-hex-32",
        description="JWT secret key for token signing (MUST change in production)",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30


# Singleton
settings = Settings()
