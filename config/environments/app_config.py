"""
SalesBoost Application Configuration
"""

from pathlib import Path
import os

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
COGNITIVE_ROOT = PROJECT_ROOT / "cognitive"
STORAGE_ROOT = PROJECT_ROOT / "storage"
CONFIG_ROOT = PROJECT_ROOT / "config"

# Environment settings
ENV = os.getenv("ENV", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Database settings
DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{STORAGE_ROOT}/databases/salesboost.db"
)

# Redis settings (for production)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Model Gateway settings
MODEL_GATEWAY_CONFIG = {
    "default_provider": "deepseek",
    "fallback_provider": "qwen",
    "budget_threshold": 10.0,
}

# Cognitive Architecture settings
COGNITIVE_CONFIG = {
    "brain": {
        "intent_confidence_threshold": 0.8,
        "coordinator_timeout": 30.0,
        "state_persistence_interval": 10.0,
    },
    "skills": {
        "study_rag_confidence": 0.85,
        "practice_simulation_depth": "advanced",
        "evaluation_dimensions": [
            "integrity",
            "relevance",
            "correctness",
            "logic",
            "compliance",
        ],
    },
    "memory": {
        "context_window_size": 10000,
        "tracking_retention_days": 90,
        "storage_backend": "sqlite",
    },
    "tools": {
        "parsers_ocr_enabled": True,
        "connectors_crm_enabled": False,
    },
    "infra": {
        "gateway_rate_limit": 100,
        "guardrails_compliance_level": "strict",
        "providers_fallback_enabled": True,
    },
    "observability": {
        "tracing_enabled": True,
        "metrics_collection_interval": 60.0,
    },
}

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },
}

# Application settings
APP_CONFIG = {
    "title": "SalesBoost - 多智能体认知链路系统",
    "description": "AI-powered sales training system with cognitive architecture",
    "version": "2.0.0",
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", "8000")),
    "cors_origins": os.getenv("CORS_ORIGINS", "*").split(","),
}

# Security settings
SECURITY_CONFIG = {
    "secret_key": os.getenv("SECRET_KEY"),
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
}

# Documentation URLs
DOCS_URL = "/docs"
REDOC_URL = "/redoc"
