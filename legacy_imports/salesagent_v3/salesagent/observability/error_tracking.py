"""Error tracking and monitoring with Sentry."""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from salesagent.core.settings import settings


def setup_sentry() -> None:
    """
    Initialize Sentry error tracking.

    Features:
    - Automatic exception capture with full stack traces
    - Performance monitoring for slow transactions
    - Breadcrumb tracking for debugging context
    - User context attachment (session_id, user_id)
    - PII filtering via before_send hook
    """
    if not settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=f"{settings.app_name}@{settings.app_version}",
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=settings.sentry_profiles_sample_rate,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],
        before_send=_before_send_filter,
        # Ignore common non-critical errors
        ignore_errors=[
            KeyboardInterrupt,
            "asyncio.CancelledError",
        ],
    )


def _before_send_filter(event: dict, hint: dict) -> dict | None:
    """
    Filter events before sending to Sentry.

    - Remove PII from request data
    - Filter out noisy errors
    - Add custom tags
    """
    # Filter PII fields
    if "request" in event:
        request_data = event["request"].get("data", {})
        for field in settings.pii_fields:
            if field in request_data:
                request_data[field] = "[FILTERED]"

    # Add custom tags
    event.setdefault("tags", {})
    event["tags"]["app_version"] = settings.app_version
    event["tags"]["environment"] = settings.environment

    return event


def set_user_context(session_id: str | None = None, user_id: str | None = None) -> None:
    """
    Set user context for error tracking.

    Args:
        session_id: Chat session ID
        user_id: Authenticated user ID
    """
    sentry_sdk.set_user({
        "id": user_id,
        "session_id": session_id,
    })


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: dict | None = None) -> None:
    """
    Add breadcrumb for debugging context.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "llm", "database", "cache")
        level: Severity level (debug, info, warning, error)
        data: Additional context data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )


def capture_exception(error: Exception, **context) -> None:
    """
    Manually capture an exception with additional context.

    Args:
        error: Exception to capture
        **context: Additional context key-value pairs
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_context(key, value)
        sentry_sdk.capture_exception(error)
