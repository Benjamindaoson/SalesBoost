"""
MCP Retry Policy - 智能重试策略

提供指数退避和抖动的重试策略。

核心功能：
1. 指数退避
2. 随机抖动
3. 可配置的重试条件
4. 重试统计

Author: Claude (Anthropic)
Version: 1.0
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryPolicy:
    """
    智能重试策略

    使用指数退避和随机抖动避免雷鸣群效应。

    Usage:
        retry_policy = RetryPolicy(max_retries=3, base_delay=1.0)

        result = await retry_policy.execute_with_retry(
            some_async_function,
            arg1, arg2,
            should_retry=lambda e: isinstance(e, TimeoutError)
        )
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry policy

        Args:
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Enable random jitter
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

        # Statistics
        self.total_attempts = 0
        self.total_retries = 0
        self.total_failures = 0

    def get_delay(self, attempt: int) -> float:
        """
        计算重试延迟（指数退避 + 抖动）

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # 指数退避
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay,
        )

        # 添加随机抖动，避免雷鸣群效应
        if self.jitter:
            # 在 [0.5 * delay, 1.5 * delay] 范围内随机
            delay = delay * (0.5 + random.random())

        return delay

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        should_retry: Optional[Callable[[Exception], bool]] = None,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        **kwargs,
    ) -> T:
        """
        执行函数，失败时重试

        Args:
            func: Async function to execute
            *args: Function arguments
            should_retry: Function to determine if should retry (optional)
            on_retry: Callback on retry (optional)
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries failed
        """
        last_exception = None
        self.total_attempts += 1

        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                last_exception = e

                # 检查是否应该重试
                if should_retry and not should_retry(e):
                    logger.info(f"Not retrying due to exception type: {type(e).__name__}")
                    raise

                # 最后一次尝试，不再重试
                if attempt >= self.max_retries:
                    self.total_failures += 1
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )
                    raise

                # 计算延迟并等待
                delay = self.get_delay(attempt)
                self.total_retries += 1

                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                # 调用回调
                if on_retry:
                    on_retry(attempt, e, delay)

                await asyncio.sleep(delay)

        # 不应该到达这里
        raise last_exception

    def get_stats(self) -> dict:
        """
        获取重试统计

        Returns:
            Statistics dict
        """
        return {
            "total_attempts": self.total_attempts,
            "total_retries": self.total_retries,
            "total_failures": self.total_failures,
            "retry_rate": self.total_retries / max(self.total_attempts, 1),
            "failure_rate": self.total_failures / max(self.total_attempts, 1),
        }

    def reset_stats(self):
        """重置统计"""
        self.total_attempts = 0
        self.total_retries = 0
        self.total_failures = 0


# 预定义的重试策略

def is_retryable_error(e: Exception) -> bool:
    """
    判断是否是可重试的错误

    Args:
        e: Exception

    Returns:
        True if retryable
    """
    # 网络错误
    if isinstance(e, (TimeoutError, ConnectionError, asyncio.TimeoutError)):
        return True

    # 临时错误（可以根据具体情况扩展）
    error_msg = str(e).lower()
    retryable_keywords = [
        "timeout",
        "connection",
        "temporary",
        "unavailable",
        "rate limit",
        "too many requests",
    ]

    return any(keyword in error_msg for keyword in retryable_keywords)


# 预定义策略实例

# 快速重试（适合轻量级操作）
FAST_RETRY = RetryPolicy(
    max_retries=2,
    base_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=True,
)

# 标准重试（适合大多数情况）
STANDARD_RETRY = RetryPolicy(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)

# 持久重试（适合重要操作）
PERSISTENT_RETRY = RetryPolicy(
    max_retries=5,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)
