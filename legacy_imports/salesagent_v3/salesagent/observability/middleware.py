"""Prometheus metrics middleware for FastAPI."""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from salesagent.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_errors_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track request metrics."""
        method = request.method
        path = request.url.path

        # Skip metrics endpoint itself
        if path == "/metrics":
            return await call_next(request)

        # Normalize path to avoid high cardinality
        endpoint = self._normalize_path(path)

        start_time = time.perf_counter()
        status_code = 500
        error_type = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error_type = type(exc).__name__
            http_request_errors_total.labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type,
            ).inc()
            raise
        finally:
            duration = time.perf_counter() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality."""
        # Remove trailing slash
        path = path.rstrip("/")

        # Replace UUIDs and IDs with placeholders
        parts = path.split("/")
        normalized = []
        for part in parts:
            if not part:
                continue
            # Check if part looks like UUID or ID
            if len(part) == 36 and part.count("-") == 4:
                normalized.append("{id}")
            elif part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)

        return "/" + "/".join(normalized) if normalized else "/"
