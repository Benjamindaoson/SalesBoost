"""
Production environment configuration
"""
import os

# Database - use PostgreSQL in production
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/salesboost")

# Debug settings
DEBUG = False
LOG_LEVEL = "INFO"

# Model Gateway - production settings
MODEL_GATEWAY_CONFIG = {
    "default_provider": "deepseek",
    "fallback_provider": "qwen",
    "budget_threshold": 50.0,
}

# CORS - specific origins in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://app.salesboost.ai").split(",")

# Security - production settings
SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in production

# Cognitive settings - optimized for production
COGNITIVE_CONFIG = {
    "brain": {
        "intent_confidence_threshold": 0.8,  # High threshold for accuracy
        "coordinator_timeout": 30.0,  # Standard timeout
        "state_persistence_interval": 10.0,  # Regular persistence
    },
    "skills": {
        "study_rag_confidence": 0.85,  # High confidence for reliable results
        "practice_simulation_depth": "advanced",  # Full-featured simulation
        "evaluation_dimensions": [
            "integrity",
            "relevance",
            "correctness",
            "logic",
            "compliance",
        ],
    },
    "memory": {
        "context_window_size": 10000,  # Full context window
        "tracking_retention_days": 90,  # Long-term tracking
        "storage_backend": "postgresql",  # Production database
    },
}

# Production-specific settings
ENABLE_PROFILING = False
ENABLE_DEVELOPER_ENDPOINTS = False
ENABLE_MOCK_RESPONSES = False

# Monitoring and observability
SENTRY_DSN = os.getenv("SENTRY_DSN")
PROMETHEUS_ENABLED = True
LOGGING_ENDPOINT = os.getenv("LOGGING_ENDPOINT")
