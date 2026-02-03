"""Lightweight Secrets Loader.

This module provides a tiny abstraction to fetch sensitive values from
environment variables. It can be extended to integrate with real secret
management systems in the future without touching the core business logic.
"""
from __future__ import annotations

import os
from typing import Optional


def load_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    """Load a secret value by name from environment variables.

    Falls back to the provided default if the secret is not set.
    """
    return os.getenv(name, default)
