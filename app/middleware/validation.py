"""
Input Validation and Rate Limiting Middleware

Provides comprehensive input validation and rate limiting for API endpoints.

Features:
- Request size limits
- Content type validation
- Rate limiting per user/IP
- DDoS protection
- Request sanitization

Usage:
    from app.middleware.validation import InputValidationMiddleware, RateLimitMiddleware

    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware)
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


# ==================== Input Validation Middleware ====================

class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input validation

    Validates:
    - Request size
    - Content type
    - Required headers
    - Malicious patterns
    """

    def __init__(
        self,
        app: ASGIApp,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        allowed_content_types: Optional[list[str]] = None,
    ):
        """
        Initialize validation middleware

        Args:
            app: ASGI application
            max_request_size: Maximum request body size in bytes
            max_file_size: Maximum file upload size in bytes
            allowed_content_types: Allowed content types (None = all)
        """
        super().__init__(app)
        self.max_request_size = max_request_size
        self.max_file_size = max_file_size
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]

        logger.info("[InputValidation] Middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request"""
        try:
            # Validate content length
            content_length = request.headers.get("content-length")

            if content_length:
                content_length = int(content_length)

                # Check if file upload
                is_file_upload = "multipart/form-data" in request.headers.get(
                    "content-type", ""
                )

                max_size = self.max_file_size if is_file_upload else self.max_request_size

                if content_length > max_size:
                    logger.warning(
                        f"[InputValidation] Request too large: {content_length} bytes "
                        f"(max: {max_size})"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "Request too large",
                            "max_size": max_size,
                            "actual_size": content_length,
                        }
                    )

            # Validate content type
            content_type = request.headers.get("content-type", "").split(";")[0].strip()

            if content_type and content_type not in self.allowed_content_types:
                logger.warning(
                    f"[InputValidation] Invalid content type: {content_type}"
                )
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error": "Unsupported content type",
                        "allowed": self.allowed_content_types,
                    }
                )

            # Validate headers for malicious patterns
            for header_name, header_value in request.headers.items():
                if self._is_malicious(header_value):
                    logger.warning(
                        f"[InputValidation] Malicious pattern detected in header: "
                        f"{header_name}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"error": "Invalid request"}
                    )

            # Process request
            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"[InputValidation] Error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error"}
            )

    def _is_malicious(self, value: str) -> bool:
        """Check for malicious patterns"""
        malicious_patterns = [
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
            "../",
            "..\\",
            "eval(",
            "exec(",
        ]

        value_lower = value.lower()

        for pattern in malicious_patterns:
            if pattern in value_lower:
                return True

        return False


# ==================== Rate Limiting Middleware ====================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting

    Implements token bucket algorithm for rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        enable_per_user: bool = True,
        enable_per_ip: bool = True,
    ):
        """
        Initialize rate limit middleware

        Args:
            app: ASGI application
            requests_per_minute: Requests allowed per minute
            burst_size: Burst size (additional requests allowed)
            enable_per_user: Enable per-user rate limiting
            enable_per_ip: Enable per-IP rate limiting
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.enable_per_user = enable_per_user
        self.enable_per_ip = enable_per_ip

        # Token buckets: {key: {"tokens": float, "last_update": float}}
        self._buckets: Dict[str, Dict[str, float]] = {}

        logger.info(
            f"[RateLimit] Middleware initialized: "
            f"{requests_per_minute} req/min, burst={burst_size}"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""
        try:
            # Get rate limit key
            rate_limit_key = self._get_rate_limit_key(request)

            if not rate_limit_key:
                # No rate limiting for this request
                return await call_next(request)

            # Check rate limit
            allowed, retry_after = self._check_rate_limit(rate_limit_key)

            if not allowed:
                logger.warning(
                    f"[RateLimit] Rate limit exceeded for key: {rate_limit_key}"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(int(retry_after)),
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                    }
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            bucket = self._buckets.get(rate_limit_key, {})
            remaining = int(bucket.get("tokens", self.burst_size))

            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

            return response

        except Exception as e:
            logger.error(f"[RateLimit] Error: {e}", exc_info=True)
            return await call_next(request)

    def _get_rate_limit_key(self, request: Request) -> Optional[str]:
        """Get rate limit key from request"""
        # Try user ID first
        if self.enable_per_user:
            user_id = request.state.__dict__.get("user_id")
            if user_id:
                return f"user:{user_id}"

        # Fall back to IP
        if self.enable_per_ip:
            client_ip = request.client.host if request.client else None
            if client_ip:
                return f"ip:{client_ip}"

        return None

    def _check_rate_limit(self, key: str) -> tuple[bool, float]:
        """
        Check rate limit using token bucket algorithm

        Args:
            key: Rate limit key

        Returns:
            (allowed, retry_after)
        """
        now = time.time()

        # Get or create bucket
        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": self.burst_size,
                "last_update": now,
            }

        bucket = self._buckets[key]

        # Calculate tokens to add
        time_passed = now - bucket["last_update"]
        tokens_to_add = time_passed * (self.requests_per_minute / 60.0)

        # Update tokens
        bucket["tokens"] = min(
            self.burst_size,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_update"] = now

        # Check if request allowed
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True, 0.0
        else:
            # Calculate retry after
            tokens_needed = 1.0 - bucket["tokens"]
            retry_after = tokens_needed / (self.requests_per_minute / 60.0)
            return False, retry_after


# ==================== Request Sanitization ====================

def sanitize_input(data: Any) -> Any:
    """
    Sanitize user input

    Args:
        data: Input data (str, dict, list, etc.)

    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        # Remove potentially dangerous characters
        data = data.replace("<", "&lt;")
        data = data.replace(">", "&gt;")
        data = data.replace("&", "&amp;")
        data = data.replace('"', "&quot;")
        data = data.replace("'", "&#x27;")
        return data

    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}

    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]

    else:
        return data


# ==================== File Upload Validation ====================

def validate_file_upload(
    filename: str,
    content_type: str,
    file_size: int,
    allowed_extensions: Optional[list[str]] = None,
    max_size: int = 50 * 1024 * 1024,  # 50MB
) -> tuple[bool, Optional[str]]:
    """
    Validate file upload

    Args:
        filename: File name
        content_type: Content type
        file_size: File size in bytes
        allowed_extensions: Allowed file extensions
        max_size: Maximum file size

    Returns:
        (is_valid, error_message)
    """
    # Check file size
    if file_size > max_size:
        return False, f"File too large (max: {max_size / 1024 / 1024:.1f}MB)"

    # Check extension
    if allowed_extensions:
        ext = filename.split(".")[-1].lower()
        if ext not in allowed_extensions:
            return False, f"File type not allowed (allowed: {', '.join(allowed_extensions)})"

    # Check for dangerous extensions
    dangerous_extensions = [
        "exe", "bat", "cmd", "sh", "ps1", "vbs", "js", "jar", "app", "deb", "rpm"
    ]

    ext = filename.split(".")[-1].lower()
    if ext in dangerous_extensions:
        return False, "Executable files are not allowed"

    return True, None
