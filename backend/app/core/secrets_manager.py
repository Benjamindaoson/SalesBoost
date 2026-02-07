"""
Enhanced Secrets Management for Production

Provides secure secrets management with support for:
- Environment variables (development)
- HashiCorp Vault (production)
- AWS Secrets Manager (cloud)
- Audit logging for secret access
"""
import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from datetime import datetime

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Centralized secrets management with multiple backend support.

    Backends (in priority order):
    1. HashiCorp Vault (if VAULT_ADDR is set)
    2. AWS Secrets Manager (if AWS_REGION is set)
    3. Environment variables (fallback)
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._audit_log: list[Dict[str, Any]] = []
        self._backend = self._detect_backend()
        logger.info(f"SecretsManager initialized with backend: {self._backend}")

    def _detect_backend(self) -> str:
        """Detect which secrets backend to use"""
        if os.getenv("VAULT_ADDR"):
            return "vault"
        elif os.getenv("AWS_REGION") and os.getenv("AWS_SECRETS_ENABLED") == "true":
            return "aws"
        else:
            return "env"

    def get_secret(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """
        Get a secret value.

        Args:
            key: Secret key name
            default: Default value if secret not found
            required: If True, raises ValueError if secret not found

        Returns:
            Secret value or default

        Raises:
            ValueError: If required=True and secret not found
        """
        # Check cache first
        if key in self._cache:
            self._log_access(key, "cache_hit")
            return self._cache[key]

        # Try to fetch from backend
        value = None
        if self._backend == "vault":
            value = self._get_from_vault(key)
        elif self._backend == "aws":
            value = self._get_from_aws(key)
        else:
            value = self._get_from_env(key)

        # Handle not found
        if value is None:
            if required:
                self._log_access(key, "not_found_required")
                raise ValueError(f"Required secret '{key}' not found")
            self._log_access(key, "not_found_default")
            return default

        # Cache and return
        self._cache[key] = value
        self._log_access(key, "success")
        return value

    def _get_from_vault(self, key: str) -> Optional[str]:
        """Get secret from HashiCorp Vault"""
        try:
            import hvac

            vault_addr = os.getenv("VAULT_ADDR")
            vault_token = os.getenv("VAULT_TOKEN")
            vault_path = os.getenv("VAULT_SECRET_PATH", "secret/data/salesboost")

            if not vault_token:
                logger.warning("VAULT_TOKEN not set, falling back to env")
                return self._get_from_env(key)

            client = hvac.Client(url=vault_addr, token=vault_token)

            if not client.is_authenticated():
                logger.error("Vault authentication failed")
                return self._get_from_env(key)

            # Read secret from Vault
            secret_response = client.secrets.kv.v2.read_secret_version(
                path=vault_path,
            )

            secrets = secret_response['data']['data']
            return secrets.get(key)

        except ImportError:
            logger.warning("hvac library not installed, install with: pip install hvac")
            return self._get_from_env(key)
        except Exception as e:
            logger.error(f"Error fetching secret from Vault: {e}")
            return self._get_from_env(key)

    def _get_from_aws(self, key: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            region = os.getenv("AWS_REGION", "us-east-1")
            secret_name = os.getenv("AWS_SECRET_NAME", "salesboost/production")

            client = boto3.client('secretsmanager', region_name=region)

            try:
                response = client.get_secret_value(SecretId=secret_name)

                # Parse JSON secrets
                import json
                secrets = json.loads(response['SecretString'])
                return secrets.get(key)

            except ClientError as e:
                logger.error(f"Error fetching secret from AWS: {e}")
                return self._get_from_env(key)

        except ImportError:
            logger.warning("boto3 library not installed, install with: pip install boto3")
            return self._get_from_env(key)
        except Exception as e:
            logger.error(f"Error fetching secret from AWS: {e}")
            return self._get_from_env(key)

    def _get_from_env(self, key: str) -> Optional[str]:
        """Get secret from environment variables (fallback)"""
        return os.getenv(key)

    def _log_access(self, key: str, status: str):
        """Log secret access for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "key": key,
            "status": status,
            "backend": self._backend
        }
        self._audit_log.append(log_entry)

        # Keep only last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

    def get_audit_log(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get recent audit log entries"""
        return self._audit_log[-limit:]

    def clear_cache(self):
        """Clear the secrets cache (useful for rotation)"""
        self._cache.clear()
        logger.info("Secrets cache cleared")


# Global singleton instance
_secrets_manager: Optional[SecretsManager] = None


@lru_cache(maxsize=1)
def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Convenience function to get a secret.

    Args:
        key: Secret key name
        default: Default value if secret not found
        required: If True, raises ValueError if secret not found

    Returns:
        Secret value or default

    Example:
        >>> api_key = get_secret("OPENAI_API_KEY", required=True)
        >>> db_password = get_secret("DB_PASSWORD", default="dev_password")
    """
    manager = get_secrets_manager()
    return manager.get_secret(key, default, required)


def rotate_secrets():
    """
    Rotate secrets by clearing cache.
    Call this when secrets are rotated in the backend.
    """
    manager = get_secrets_manager()
    manager.clear_cache()
    logger.info("Secrets rotated successfully")
