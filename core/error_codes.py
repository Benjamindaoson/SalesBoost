"""Unified error codes for API responses.

This enum centralizes error codes used across the API surface. It enables
consumers and tooling to rely on a stable set of error identifiers.
"""
from __future__ import annotations

from enum import Enum


class ERROR_CODE(str, Enum):
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    NOT_FOUND = "NOT_FOUND"
    REQUEST_ENTITY_TOO_LARGE = "REQUEST_ENTITY_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
