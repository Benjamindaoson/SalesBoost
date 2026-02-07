"""
Concurrency Optimization

并发优化系统 - 连接池、限流、熔断

Author: Claude (Anthropic)
Date: 2026-02-05
"""

import asyncio
import logging
import time
from collections import deque
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


# ============================================
# 异步连接池管理
# ============================================

class AsyncConnectionPool:
    """
    异步连接池

    管理数据库、Redis、HTTP等连接的复用
    """

    def __init__(
        self,
        create_connection: Callable,
        max_size: int = 10,
        min_size: int = 2,
        max_idle_time: int = 300,
    ):
        """
        初始化连接池

        Args:
            create_connection: 创建连接的函数
            max_size: 最大连接数
            min_size: 最小连接数
            max_idle_time: 最大空闲时间（秒）
        """
        self.create_connection = create_connection
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time

        self._pool: deque = deque()
        self._in_use: set = set()
        self._lock = asyncio.Lock()

        logger.info(
            f"AsyncConnectionPool initialized: "
            f"max_size={max_size}, min_size={min_size}"
        )

    async def acquire(self) -> Any:
        """
        获取连接

        Returns:
            连接对象
        """
        async with self._lock:
            # 1. 尝试从池中获取空闲连接
            while self._pool:
                conn, last_used = self._pool.popleft()

                # 检查连接是否过期
                if time.time() - last_used < self.max_idle_time:
                    self._in_use.add(conn)
                    return conn
                else:
                    # 连接过期，关闭
                    await self._close_connection(conn)

            # 2. 池中无可用连接，创建新连接
            if len(self._in_use) < self.max_size:
                conn = await self.create_connection()
                self._in_use.add(conn)
                return conn

            # 3. 达到最大连接数，等待
            raise Exception("Connection pool exhausted")

    async def release(self, conn: Any) -> None:
        """
        释放连接

        Args:
            conn: 连接对象
        """
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._pool.append((conn, time.time()))

    async def _close_connection(self, conn: Any) -> None:
        """
        关闭连接

        Args:
            conn: 连接对象
        """
        try:
            if hasattr(conn, 'close'):
                await conn.close()
        except Exception as e:
            logger.error(f"Failed to close connection: {e}")

    async def close_all(self) -> None:
        """关闭所有连接"""
        async with self._lock:
            # 关闭空闲连接
            while self._pool:
                conn, _ = self._pool.popleft()
                await self._close_connection(conn)

            # 关闭使用中的连接
            for conn in self._in_use:
                await self._close_connection(conn)

            self._in_use.clear()

        logger.info("All connections closed")


# ============================================
# 令牌桶限流器
# ============================================

class TokenBucketRateLimiter:
    """
    令牌桶限流器

    平滑限流，允许突发流量
    """

    def __init__(
        self,
        rate: float,
        capacity: int,
    ):
        """
        初始化限流器

        Args:
            rate: 令牌生成速率（个/秒）
            capacity: 桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

        logger.info(
            f"TokenBucketRateLimiter initialized: "
            f"rate={rate}/s, capacity={capacity}"
        )

    async def acquire(self, tokens: int = 1) -> bool:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数

        Returns:
            是否成功获取
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # 补充令牌
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            # 检查是否有足够的令牌
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

    async def wait_for_token(self, tokens: int = 1, timeout: float = 10.0) -> bool:
        """
        等待令牌（阻塞）

        Args:
            tokens: 需要的令牌数
            timeout: 超时时间（秒）

        Returns:
            是否成功获取
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if await self.acquire(tokens):
                return True

            # 等待一小段时间
            await asyncio.sleep(0.1)

        return False


# ============================================
# 熔断器
# ============================================

class CircuitBreaker:
    """
    熔断器

    防止级联故障，保护系统稳定性
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

        logger.info(
            f"CircuitBreaker initialized: "
            f"threshold={failure_threshold}, timeout={recovery_timeout}s"
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            Exception: 熔断器打开时抛出异常
        """
        # 检查熔断器状态
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info("CircuitBreaker: Attempting reset (half-open)")
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable (circuit breaker open)"
                )

        try:
            # 调用函数
            result = await func(*args, **kwargs)

            # 成功 - 重置失败计数
            if self.state == "half_open":
                self._reset()
                logger.info("CircuitBreaker: Reset successful (closed)")

            return result

        except self.expected_exception as e:
            # 失败 - 增加失败计数
            self._record_failure()
            raise e

    def _record_failure(self) -> None:
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"CircuitBreaker: Opened after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.last_failure_time is None:
            return False

        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _reset(self) -> None:
        """重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"


# ============================================
# 限流中间件
# ============================================

class RateLimitMiddleware:
    """
    限流中间件

    基于IP或用户的请求限流
    """

    def __init__(
        self,
        rate: float = 100.0,  # 每秒请求数
        capacity: int = 200,  # 桶容量
    ):
        """
        初始化限流中间件

        Args:
            rate: 令牌生成速率
            capacity: 桶容量
        """
        self.rate = rate
        self.capacity = capacity
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}

    async def __call__(self, request: Request, call_next):
        """
        处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件

        Returns:
            响应对象
        """
        # 获取客户端标识（IP或用户ID）
        client_id = self._get_client_id(request)

        # 获取或创建限流器
        if client_id not in self.limiters:
            self.limiters[client_id] = TokenBucketRateLimiter(
                rate=self.rate,
                capacity=self.capacity,
            )

        limiter = self.limiters[client_id]

        # 尝试获取令牌
        if not await limiter.acquire():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "1"},
            )

        # 继续处理请求
        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """
        获取客户端标识

        Args:
            request: 请求对象

        Returns:
            客户端标识
        """
        # 优先使用用户ID
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"

        # 否则使用IP地址
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0]}"

        return f"ip:{request.client.host}"


# ============================================
# 并发控制装饰器
# ============================================

def with_concurrency_limit(max_concurrent: int = 10):
    """
    并发控制装饰器

    限制同时执行的任务数量

    Args:
        max_concurrent: 最大并发数

    Returns:
        装饰器函数
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            async with semaphore:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================
# 批处理优化
# ============================================

class BatchProcessor:
    """
    批处理器

    将多个请求合并为一个批次处理，提升效率
    """

    def __init__(
        self,
        process_func: Callable,
        batch_size: int = 10,
        max_wait_time: float = 0.1,
    ):
        """
        初始化批处理器

        Args:
            process_func: 批处理函数
            batch_size: 批次大小
            max_wait_time: 最大等待时间（秒）
        """
        self.process_func = process_func
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time

        self.queue: deque = deque()
        self.futures: Dict[int, asyncio.Future] = {}
        self.next_id = 0
        self._lock = asyncio.Lock()
        self._processing = False

    async def submit(self, item: Any) -> Any:
        """
        提交项目到批处理队列

        Args:
            item: 要处理的项目

        Returns:
            处理结果
        """
        async with self._lock:
            # 分配ID
            item_id = self.next_id
            self.next_id += 1

            # 添加到队列
            self.queue.append((item_id, item))

            # 创建Future
            future = asyncio.Future()
            self.futures[item_id] = future

            # 触发处理
            if not self._processing:
                asyncio.create_task(self._process_batch())

        # 等待结果
        return await future

    async def _process_batch(self) -> None:
        """处理批次"""
        self._processing = True

        # 等待批次填满或超时
        await asyncio.sleep(self.max_wait_time)

        async with self._lock:
            if not self.queue:
                self._processing = False
                return

            # 取出一批
            batch = []
            batch_ids = []

            while self.queue and len(batch) < self.batch_size:
                item_id, item = self.queue.popleft()
                batch.append(item)
                batch_ids.append(item_id)

        # 批量处理
        try:
            results = await self.process_func(batch)

            # 设置结果
            for item_id, result in zip(batch_ids, results):
                if item_id in self.futures:
                    self.futures[item_id].set_result(result)
                    del self.futures[item_id]

        except Exception as e:
            # 设置异常
            for item_id in batch_ids:
                if item_id in self.futures:
                    self.futures[item_id].set_exception(e)
                    del self.futures[item_id]

        self._processing = False

        # 如果还有待处理项目，继续处理
        if self.queue:
            asyncio.create_task(self._process_batch())


# 使用示例
async def example_usage():
    """使用示例"""
    # 1. 连接池
    async def create_db_connection():
        # 创建数据库连接
        return "db_connection"

    pool = AsyncConnectionPool(create_db_connection, max_size=10)
    conn = await pool.acquire()
    # 使用连接...
    await pool.release(conn)

    # 2. 限流器
    limiter = TokenBucketRateLimiter(rate=10.0, capacity=20)
    if await limiter.acquire():
        # 执行操作
        pass

    # 3. 熔断器
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    async def risky_operation():
        # 可能失败的操作
        pass

    result = await breaker.call(risky_operation)

    # 4. 批处理
    async def batch_process(items):
        # 批量处理
        return [f"processed_{item}" for item in items]

    processor = BatchProcessor(batch_process, batch_size=10)
    result = await processor.submit("item1")


if __name__ == "__main__":
    asyncio.run(example_usage())
