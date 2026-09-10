"""Unified exception hierarchy for SalesAgent V3."""
from __future__ import annotations


class SalesAgentError(Exception):
    """Base exception for all SalesAgent errors."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


# ── FSM Exceptions ────────────────────────────────────────────────────────────

class FSMError(SalesAgentError):
    """Base FSM error."""
    error_code = "FSM_ERROR"


class InvalidTransitionError(FSMError):
    """Invalid stage transition attempt."""
    status_code = 400
    error_code = "INVALID_TRANSITION"


class SessionNotFoundError(SalesAgentError):
    """Conversation session not found."""
    status_code = 404
    error_code = "SESSION_NOT_FOUND"


# ── LLM / Gateway Exceptions ─────────────────────────────────────────────────

class GatewayError(SalesAgentError):
    """Model gateway error."""
    error_code = "GATEWAY_ERROR"


class GatewayTimeoutError(GatewayError):
    """Model call timed out across all fallback attempts."""
    status_code = 504
    error_code = "GATEWAY_TIMEOUT"


class ModelUnavailableError(GatewayError):
    """All models in the fallback chain are unavailable."""
    status_code = 503
    error_code = "MODEL_UNAVAILABLE"


# ── Reasoning Exceptions ─────────────────────────────────────────────────────

class ReasoningError(SalesAgentError):
    """Reasoning chain error."""
    error_code = "REASONING_ERROR"


class ReasoningSchemaError(ReasoningError):
    """Reasoning output failed schema validation; falling back to defaults."""
    error_code = "REASONING_SCHEMA_ERROR"


# ── Guard Exceptions ─────────────────────────────────────────────────────────

class GuardError(SalesAgentError):
    """Streaming guard error."""
    error_code = "GUARD_ERROR"


# ── Knowledge Exceptions ─────────────────────────────────────────────────────

class KnowledgeError(SalesAgentError):
    """Knowledge base error."""
    error_code = "KNOWLEDGE_ERROR"


class DocumentProcessingError(KnowledgeError):
    """Document chunking/indexing failed."""
    error_code = "DOCUMENT_PROCESSING_ERROR"


# ── Database Exceptions ───────────────────────────────────────────────────────

class DatabaseError(SalesAgentError):
    """Database operation error."""
    error_code = "DATABASE_ERROR"


# ── Validation Exceptions ─────────────────────────────────────────────────────

class ValidationError(SalesAgentError):
    """Request validation error."""
    status_code = 422
    error_code = "VALIDATION_ERROR"
