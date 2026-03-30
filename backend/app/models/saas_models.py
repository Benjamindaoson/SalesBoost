"""
SaaS Models - Compatibility layer

This module provides backward compatibility for code that imports from saas_models.
It re-exports models from their actual locations.
"""

from .user import User, UserRole

__all__ = ["User", "UserRole"]
