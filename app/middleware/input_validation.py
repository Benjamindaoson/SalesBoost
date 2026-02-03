"""Input validation middleware for early request sanitation.

- Enforces max request body size to protect against oversized payloads.
- Enforces allowed content-types for requests with bodies.
- Logs sanitized request metadata (query/headers with sensitive data masked).
- Does not consume the request body to avoid interfering with downstream handlers.
"""
from __future__ import annotations

import logging
from typing import Dict

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

MAX_BODY_SIZE = 1_000_000  # 1 MB
SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie"}


class InputValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Enforce max body size if a body is present
        content_length = request.headers.get("content-length")
        try:
            length = int(content_length) if content_length else 0
        except Exception:
            length = 0
        if length > MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error": {"code": "REQUEST_ENTITY_TOO_LARGE", "message": "Request body too large"},
                },
            )

        # Enforce allowed content types for requests with a body
        method = request.method.upper()
        if method in {"POST", "PUT", "PATCH", "DELETE"} and length > 0:
            content_type = (request.headers.get("content-type") or "").lower()
            allowed = (
                content_type.startswith("application/json")
                or content_type.startswith("multipart/form-data")
                or content_type.startswith("application/x-www-form-urlencoded")
            )
            if not allowed:
                return JSONResponse(
                    status_code=415,
                    content={
                        "success": False,
                        "error": {
                            "code": "UNSUPPORTED_MEDIA_TYPE",
                            "message": "Unsupported Media Type",
                        },
                    },
                )

        # Sanitize and log non-sensitive request metadata
        try:
            query = dict(request.query_params)
            headers = {
                k: ("******" if k.lower() in SENSITIVE_HEADERS else v)
                for k, v in request.headers.items()
            }
            logger.info("Request start: method=%s path=%s query=%s headers=%s", method, request.url.path, query, headers)
        except Exception:
            pass

        response = await call_next(request)
        return response
