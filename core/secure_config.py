"""
Secure Configuration Loader

This module enhances the Settings class to load sensitive values from
secrets manager instead of environment variables.

Usage:
    from core.secure_config import get_secure_settings

    settings = get_secure_settings()
    api_key = settings.OPENAI_API_KEY  # Loaded from secrets manager
"""

import logging
from typing import Optional
from functools import lru_cache

from core.config import Settings, get_settings
from core.secrets_manager import get_secrets_manager

logger = logging.getLogger(__name__)


class SecureSettings(Settings):
    """
    Enhanced Settings that loads sensitive values from secrets manager

    Sensitive fields (API keys, passwords, etc.) are loaded from:
    1. Secrets manager (Vault/AWS Secrets Manager) if configured
    2. Environment variables (fallback)

    Non-sensitive fields are loaded normally from environment variables.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._secrets_manager = get_secrets_manager()
        self._load_secrets()

    def _load_secrets(self):
        """Load sensitive values from secrets manager"""
        # List of sensitive fields to load from secrets manager
        sensitive_fields = [
            # Security
            "SECRET_KEY",
            "ADMIN_PASSWORD",
            "ADMIN_PASSWORD_HASH",

            # LLM API Keys
            "OPENAI_API_KEY",
            "GOOGLE_API_KEY",
            "SILICONFLOW_API_KEY",

            # Database
            "DATABASE_URL",

            # Redis
            "REDIS_URL",

            # External Services
            "SUPABASE_KEY",
            "SUPABASE_JWT_SECRET",
            "QDRANT_API_KEY",

            # Monitoring
            "SENTRY_DSN",
            "JAEGER_ENDPOINT",
        ]

        for field in sensitive_fields:
            # Get current value (from env or default)
            current_value = getattr(self, field, None)

            # Try to load from secrets manager
            try:
                secret_value = self._secrets_manager.get_secret(
                    field,
                    default=current_value
                )

                # Only update if secret was found
                if secret_value is not None:
                    setattr(self, field, secret_value)
                    logger.debug(f"Loaded {field} from secrets manager")

            except Exception as e:
                logger.warning(
                    f"Failed to load {field} from secrets manager: {e}. "
                    f"Using environment variable."
                )

    def rotate_secrets(self):
        """
        Rotate secrets by reloading from secrets manager

        Call this when secrets are rotated in the backend.
        """
        self._secrets_manager.clear_cache()
        self._load_secrets()
        logger.info("Secrets rotated successfully")


# Global singleton instance
_secure_settings: Optional[SecureSettings] = None


@lru_cache(maxsize=1)
def get_secure_settings() -> SecureSettings:
    """
    Get the global secure settings instance

    Returns:
        SecureSettings instance with secrets loaded from secrets manager

    Example:
        >>> settings = get_secure_settings()
        >>> api_key = settings.OPENAI_API_KEY  # Loaded from Vault/AWS
    """
    global _secure_settings
    if _secure_settings is None:
        _secure_settings = SecureSettings()
    return _secure_settings


def use_secure_settings():
    """
    Replace the default settings with secure settings globally

    Call this at application startup to enable secrets manager.

    Example:
        # In main.py
        from core.secure_config import use_secure_settings
        use_secure_settings()
    """
    import core.config
    core.config._settings = get_secure_settings()
    logger.info("Secure settings enabled (using secrets manager)")


def rotate_application_secrets():
    """
    Rotate all application secrets

    Call this when secrets are rotated in the backend (Vault/AWS).
    """
    settings = get_secure_settings()
    settings.rotate_secrets()
    logger.info("Application secrets rotated")
