"""
Tool Rate Limiter

Implements token bucket algorithm for rate limiting tool executions.
Prevents abuse and ensures fair resource allocation.
"""
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass

from core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int  # Maximum tokens
    tokens: float  # Current tokens
    refill_rate: float  # Tokens per second
    last_refill: float  # Last refill timestamp

    def refill(self) -> None:
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns:
            True if tokens consumed, False if insufficient tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens available.

        Returns:
            Seconds to wait, 0 if tokens available now
        """
        self.refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class ToolRateLimiter:
    """
    Rate limiter for tool executions using token bucket algorithm.

    Configuration per tool:
    - knowledge_retriever: 10 calls/min
    - crm_integration: 5 calls/min
    - sms_outreach: 20 calls/hour
    - compliance_check: 15 calls/min
    - profile_reader: 20 calls/min
    - price_calculator: 30 calls/min
    - stage_classifier: 10 calls/min
    - competitor_analysis: 5 calls/min
    """

    # Default rate limits (calls per minute)
    DEFAULT_LIMITS = {
        "knowledge_retriever": (10, 60),  # 10 calls per 60 seconds
        "crm_integration": (5, 60),
        "sms_outreach": (20, 3600),  # 20 calls per hour
        "compliance_check": (15, 60),
        "profile_reader": (20, 60),
        "price_calculator": (30, 60),
        "stage_classifier": (10, 60),
        "competitor_analysis": (5, 60),
    }

    def __init__(self, custom_limits: Optional[Dict[str, tuple]] = None):
        """
        Initialize rate limiter.

        Args:
            custom_limits: Optional custom limits per tool
                Format: {"tool_name": (calls, seconds)}
        """
        self._buckets: Dict[str, TokenBucket] = {}
        self._limits = {**self.DEFAULT_LIMITS}

        if custom_limits:
            self._limits.update(custom_limits)

        logger.info(f"ToolRateLimiter initialized with {len(self._limits)} tool limits")

    def _get_bucket(self, tool_name: str) -> TokenBucket:
        """Get or create token bucket for tool"""
        if tool_name not in self._buckets:
            # Get limit configuration
            if tool_name in self._limits:
                calls, seconds = self._limits[tool_name]
            else:
                # Default: 10 calls per minute
                calls, seconds = 10, 60

            refill_rate = calls / seconds

            self._buckets[tool_name] = TokenBucket(
                capacity=calls,
                tokens=calls,  # Start with full bucket
                refill_rate=refill_rate,
                last_refill=time.time()
            )

            logger.debug(f"Created token bucket for {tool_name}: {calls} calls per {seconds}s")

        return self._buckets[tool_name]

    async def check_limit(self, tool_name: str, tokens: int = 1) -> tuple[bool, Optional[float]]:
        """
        Check if tool execution is allowed.

        Args:
            tool_name: Name of the tool
            tokens: Number of tokens to consume (default 1)

        Returns:
            Tuple of (allowed, retry_after)
            - allowed: True if execution allowed
            - retry_after: Seconds to wait if not allowed, None if allowed
        """
        settings = get_settings()

        # Check if rate limiting is enabled
        if not settings.TOOL_RATE_LIMIT_ENABLED:
            return True, None

        bucket = self._get_bucket(tool_name)

        if bucket.consume(tokens):
            logger.debug(f"Rate limit check passed for {tool_name} (tokens remaining: {bucket.tokens:.2f})")
            return True, None
        else:
            wait_time = bucket.get_wait_time(tokens)
            logger.warning(
                f"Rate limit exceeded for {tool_name}. "
                f"Retry after {wait_time:.2f}s (tokens: {bucket.tokens:.2f}/{bucket.capacity})"
            )
            return False, wait_time

    def get_status(self, tool_name: str) -> Dict:
        """
        Get rate limit status for a tool.

        Returns:
            Dictionary with current status
        """
        if tool_name not in self._buckets:
            if tool_name in self._limits:
                calls, seconds = self._limits[tool_name]
                return {
                    "tool": tool_name,
                    "limit": f"{calls} calls per {seconds}s",
                    "available": calls,
                    "capacity": calls,
                    "refill_rate": calls / seconds
                }
            return {
                "tool": tool_name,
                "limit": "No limit configured",
                "available": "unlimited",
                "capacity": "unlimited"
            }

        bucket = self._get_bucket(tool_name)
        bucket.refill()

        return {
            "tool": tool_name,
            "available": round(bucket.tokens, 2),
            "capacity": bucket.capacity,
            "refill_rate": round(bucket.refill_rate, 4),
            "utilization": round((bucket.capacity - bucket.tokens) / bucket.capacity * 100, 2)
        }

    def get_all_status(self) -> Dict[str, Dict]:
        """Get status for all tools"""
        return {
            tool_name: self.get_status(tool_name)
            for tool_name in self._limits.keys()
        }

    def reset(self, tool_name: Optional[str] = None) -> None:
        """
        Reset rate limiter.

        Args:
            tool_name: Specific tool to reset, or None to reset all
        """
        if tool_name:
            if tool_name in self._buckets:
                bucket = self._buckets[tool_name]
                bucket.tokens = bucket.capacity
                bucket.last_refill = time.time()
                logger.info(f"Reset rate limiter for {tool_name}")
        else:
            for bucket in self._buckets.values():
                bucket.tokens = bucket.capacity
                bucket.last_refill = time.time()
            logger.info("Reset all rate limiters")


# Global singleton instance
_rate_limiter: Optional[ToolRateLimiter] = None


def get_rate_limiter() -> ToolRateLimiter:
    """Get global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ToolRateLimiter()
    return _rate_limiter
