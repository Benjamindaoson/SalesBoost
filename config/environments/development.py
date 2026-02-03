"""
Development environment configuration
"""

# Database
DATABASE_URL = "sqlite:///data/databases/salesboost.db"

# Debug settings
DEBUG = True
LOG_LEVEL = "DEBUG"

# Model Gateway - use cheaper models for development
MODEL_GATEWAY_CONFIG = {
    "default_provider": "mock",
    "fallback_provider": "deepseek",
    "budget_threshold": 5.0,
}

# CORS - allow all origins in development
CORS_ORIGINS = ["*"]

# Security - relaxed for development
SECRET_KEY = "development-secret-key-change-in-production"

# Cognitive settings - optimized for development
COGNITIVE_CONFIG = {
    "brain": {
        "intent_confidence_threshold": 0.6,  # Lower threshold for easier testing
        "coordinator_timeout": 60.0,  # Longer timeout for debugging
        "state_persistence_interval": 5.0,  # More frequent saves
    },
    "skills": {
        "study_rag_confidence": 0.7,  # Lower confidence for more results
        "practice_simulation_depth": "basic",  # Faster simulation
        "evaluation_dimensions": [
            "integrity",
            "relevance",
            "correctness",
            "logic",
            "compliance",
        ],
    },
    "memory": {
        "context_window_size": 5000,  # Smaller window for faster processing
        "tracking_retention_days": 7,  # Shorter retention for development
        "storage_backend": "sqlite",
    },
}

# Development-specific features
ENABLE_PROFILING = True
ENABLE_DEVELOPER_ENDPOINTS = True
ENABLE_MOCK_RESPONSES = False
