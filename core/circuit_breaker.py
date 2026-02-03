"""
Circuit Breaker Pattern Implementation
用于模型调用的熔断与故障恢复
"""
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    CLOSED = "closed"     # 正常状态
    OPEN = "open"         # 熔断状态
    HALF_OPEN = "half_open" # 半开状态（尝试恢复）

@dataclass
class CircuitStats:
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0
    state: CircuitState = CircuitState.CLOSED

class CircuitBreaker:
    """
    断路器管理器
    
    配置：
    - failure_threshold: 连续失败次数阈值，超过则熔断
    - recovery_timeout: 熔断后等待恢复的时间（秒）
    - half_open_attempts: 半开状态下允许尝试的次数
    """
    
    def __init__(
        self, 
        failure_threshold: int = 3, 
        recovery_timeout: float = 30.0,
        half_open_attempts: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts
        self._circuits: Dict[str, CircuitStats] = {}
        
    def get_key(self, provider: Any, model: str) -> str:
        # Handle ProviderType enum or string
        provider_str = provider.value if hasattr(provider, "value") else str(provider)
        return f"{provider_str}:{model}"

    def is_available(self, provider: Any, model: str) -> bool:
        """检查服务是否可用"""
        key = self.get_key(provider, model)
        if key not in self._circuits:
            return True
            
        stats = self._circuits[key]
        
        if stats.state == CircuitState.CLOSED:
            return True
            
        if stats.state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if time.time() - stats.last_failure_time > self.recovery_timeout:
                logger.info(f"Circuit {key} entering HALF_OPEN state")
                stats.state = CircuitState.HALF_OPEN
                stats.success_count = 0 # 重置成功计数，用于半开检测
                return True
            return False
            
        if stats.state == CircuitState.HALF_OPEN:
            # 半开状态下，限制并发/尝试次数（简单实现：允许通过）
            return True
            
        return True

    def record_success(self, provider: Any, model: str):
        """记录成功调用"""
        key = self.get_key(provider, model)
        if key not in self._circuits:
            return

        stats = self._circuits[key]
        
        if stats.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit {key} recovered (HALF_OPEN -> CLOSED)")
            stats.state = CircuitState.CLOSED
            stats.failure_count = 0
            stats.success_count = 0
        elif stats.state == CircuitState.CLOSED:
            stats.failure_count = 0 # 连续失败中断

    def record_failure(self, provider: Any, model: str, error: Optional[Exception] = None):
        """记录失败调用"""
        key = self.get_key(provider, model)
        if key not in self._circuits:
            self._circuits[key] = CircuitStats()
            
        stats = self._circuits[key]
        stats.last_failure_time = time.time()
        
        if stats.state == CircuitState.CLOSED:
            stats.failure_count += 1
            if stats.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit {key} OPENED due to {stats.failure_count} failures. Last error: {error}")
                stats.state = CircuitState.OPEN
        
        elif stats.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {key} failed in HALF_OPEN, returning to OPEN. Error: {error}")
            stats.state = CircuitState.OPEN # 半开失败，立即回退到 OPEN

# Global instance
circuit_breaker = CircuitBreaker()
