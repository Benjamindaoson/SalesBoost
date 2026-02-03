"""
Circuit Breaker Implementation

Provides circuit breaker pattern for external service calls to prevent
cascading failures.

Features:
- Automatic failure detection
- Circuit states: CLOSED, OPEN, HALF_OPEN
- Configurable thresholds
- Fallback support
- Metrics tracking

Architecture:
    Service Call → Circuit Breaker → External Service
                 ↓ (if OPEN)
              Fallback

Usage:
    from app.infra.resilience.circuit_breaker import CircuitBreakerManager

    breaker_mgr = CircuitBreakerManager()
    breaker = breaker_mgr.get_breaker("llm_service")

    result = await breaker.call(llm_api_function, *args)
"""

import logging
import time
from typing import Any, Callable, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio

try:
    import pybreaker
except ImportError:
    pybreaker = None
    logging.warning("pybreaker not installed. Install with: pip install pybreaker")

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    fail_max: int = 5  # Failures before opening
    timeout_duration: int = 60  # Seconds to wait before half-open
    reset_timeout: int = 60  # Seconds in half-open before closing
    expected_exception: type = Exception  # Exception type to catch
    name: str = "default"


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for external service calls

    Implements the circuit breaker pattern to prevent cascading failures.
    """

    def __init__(self, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker

        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.metrics = CircuitBreakerMetrics()

        # Use pybreaker if available
        if pybreaker:
            self._breaker = pybreaker.CircuitBreaker(
                fail_max=config.fail_max,
                timeout_duration=config.timeout_duration,
                reset_timeout=config.reset_timeout,
                expected_exception=config.expected_exception,
                name=config.name,
                listeners=[self._create_listener()],
            )
        else:
            self._breaker = None
            logger.warning(
                f"[CircuitBreaker:{config.name}] pybreaker not available, "
                f"using fallback implementation"
            )

        logger.info(f"[CircuitBreaker:{config.name}] Initialized")

    def _create_listener(self):
        """Create pybreaker listener for metrics"""
        if not pybreaker:
            return None

        class MetricsListener(pybreaker.CircuitBreakerListener):
            def __init__(self, metrics: CircuitBreakerMetrics):
                self.metrics = metrics

            def state_change(self, cb, old_state, new_state):
                if new_state == pybreaker.STATE_OPEN:
                    self.metrics.state = CircuitState.OPEN
                    self.metrics.opened_at = datetime.utcnow()
                elif new_state == pybreaker.STATE_HALF_OPEN:
                    self.metrics.state = CircuitState.HALF_OPEN
                elif new_state == pybreaker.STATE_CLOSED:
                    self.metrics.state = CircuitState.CLOSED

            def before_call(self, cb, func, *args, **kwargs):
                self.metrics.total_calls += 1

            def success(self, cb):
                self.metrics.success_count += 1
                self.metrics.total_successes += 1
                self.metrics.last_success_time = datetime.utcnow()

            def failure(self, cb, exception):
                self.metrics.failure_count += 1
                self.metrics.total_failures += 1
                self.metrics.last_failure_time = datetime.utcnow()

        return MetricsListener(self.metrics)

    async def call(
        self,
        func: Callable,
        *args,
        fallback: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to call
            *args: Function arguments
            fallback: Fallback function if circuit is open
            **kwargs: Function keyword arguments

        Returns:
            Function result or fallback result

        Raises:
            Exception: If circuit is open and no fallback provided
        """
        if self._breaker:
            # Use pybreaker
            try:
                if asyncio.iscoroutinefunction(func):
                    return await self._breaker.call_async(func, *args, **kwargs)
                else:
                    return self._breaker.call(func, *args, **kwargs)

            except pybreaker.CircuitBreakerError as e:
                logger.warning(
                    f"[CircuitBreaker:{self.config.name}] Circuit is OPEN: {e}"
                )

                if fallback:
                    logger.info(
                        f"[CircuitBreaker:{self.config.name}] Using fallback"
                    )
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    else:
                        return fallback(*args, **kwargs)
                else:
                    raise

        else:
            # Fallback implementation (simple)
            try:
                self.metrics.total_calls += 1

                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self.metrics.success_count += 1
                self.metrics.total_successes += 1
                self.metrics.last_success_time = datetime.utcnow()

                # Reset failure count on success
                if self.metrics.state == CircuitState.HALF_OPEN:
                    self.metrics.state = CircuitState.CLOSED
                    self.metrics.failure_count = 0

                return result

            except Exception as e:
                self.metrics.failure_count += 1
                self.metrics.total_failures += 1
                self.metrics.last_failure_time = datetime.utcnow()

                # Check if should open circuit
                if self.metrics.failure_count >= self.config.fail_max:
                    self.metrics.state = CircuitState.OPEN
                    self.metrics.opened_at = datetime.utcnow()
                    logger.warning(
                        f"[CircuitBreaker:{self.config.name}] Circuit OPENED "
                        f"after {self.metrics.failure_count} failures"
                    )

                # Check if circuit is open
                if self.metrics.state == CircuitState.OPEN:
                    # Check if timeout expired
                    if self.metrics.opened_at:
                        elapsed = (datetime.utcnow() - self.metrics.opened_at).total_seconds()
                        if elapsed > self.config.timeout_duration:
                            self.metrics.state = CircuitState.HALF_OPEN
                            logger.info(
                                f"[CircuitBreaker:{self.config.name}] "
                                f"Circuit HALF_OPEN for testing"
                            )

                    # Use fallback if available
                    if fallback:
                        logger.info(
                            f"[CircuitBreaker:{self.config.name}] Using fallback"
                        )
                        if asyncio.iscoroutinefunction(fallback):
                            return await fallback(*args, **kwargs)
                        else:
                            return fallback(*args, **kwargs)

                raise

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.metrics.state

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics"""
        return self.metrics

    def reset(self):
        """Reset circuit breaker"""
        if self._breaker:
            self._breaker.close()

        self.metrics = CircuitBreakerMetrics()
        logger.info(f"[CircuitBreaker:{self.config.name}] Reset")


# ==================== Circuit Breaker Manager ====================

class CircuitBreakerManager:
    """
    Manages multiple circuit breakers

    Provides centralized management of circuit breakers for different services.
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = {}

        # Register default breakers
        self._register_default_breakers()

        logger.info("[CircuitBreakerManager] Initialized")

    def _register_default_breakers(self):
        """Register default circuit breakers for common services"""
        # LLM services
        self.register(
            "llm_openai",
            CircuitBreakerConfig(
                name="llm_openai",
                fail_max=5,
                timeout_duration=60,
            )
        )

        self.register(
            "llm_gemini",
            CircuitBreakerConfig(
                name="llm_gemini",
                fail_max=5,
                timeout_duration=60,
            )
        )

        self.register(
            "llm_siliconflow",
            CircuitBreakerConfig(
                name="llm_siliconflow",
                fail_max=5,
                timeout_duration=60,
            )
        )

        # Vector store
        self.register(
            "qdrant",
            CircuitBreakerConfig(
                name="qdrant",
                fail_max=3,
                timeout_duration=30,
            )
        )

        # Redis
        self.register(
            "redis",
            CircuitBreakerConfig(
                name="redis",
                fail_max=3,
                timeout_duration=30,
            )
        )

        # Database
        self.register(
            "database",
            CircuitBreakerConfig(
                name="database",
                fail_max=3,
                timeout_duration=30,
            )
        )

        # OCR service
        self.register(
            "ocr_service",
            CircuitBreakerConfig(
                name="ocr_service",
                fail_max=3,
                timeout_duration=60,
            )
        )

    def register(self, name: str, config: CircuitBreakerConfig):
        """Register a circuit breaker"""
        self._configs[name] = config
        logger.debug(f"[CircuitBreakerManager] Registered: {name}")

    def get_breaker(self, name: str) -> CircuitBreaker:
        """
        Get circuit breaker by name

        Args:
            name: Circuit breaker name

        Returns:
            CircuitBreaker instance

        Raises:
            ValueError: If breaker not registered
        """
        if name not in self._breakers:
            config = self._configs.get(name)

            if config is None:
                raise ValueError(f"Circuit breaker not registered: {name}")

            self._breakers[name] = CircuitBreaker(config)

        return self._breakers[name]

    def get_all_metrics(self) -> Dict[str, CircuitBreakerMetrics]:
        """Get metrics for all circuit breakers"""
        return {
            name: breaker.get_metrics()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()

        logger.info("[CircuitBreakerManager] Reset all breakers")


# ==================== Global Instance ====================

_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """
    Get global circuit breaker manager (singleton)

    Returns:
        CircuitBreakerManager instance
    """
    global _breaker_manager

    if _breaker_manager is None:
        _breaker_manager = CircuitBreakerManager()

    return _breaker_manager


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """
    Convenience function to get circuit breaker

    Args:
        name: Circuit breaker name

    Returns:
        CircuitBreaker instance
    """
    manager = get_circuit_breaker_manager()
    return manager.get_breaker(name)
