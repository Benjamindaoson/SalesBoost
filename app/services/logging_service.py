"""
Structured Logging Service - 结构化日志服务
提供统一的日志格式、级别管理和输出配置
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        # 清除现有处理器
        self.logger.handlers.clear()

        # 创建格式化器
        try:
            from pythonjsonlogger import jsonlogger

            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        except ImportError:
            # 如果没有安装pythonjsonlogger，使用标准格式
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 设置日志级别
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(level)

    def log_request(self, request_data: Dict[str, Any]):
        """记录请求日志"""
        self.logger.info("API Request", extra={"event_type": "api_request", "data": request_data})

    def log_response(self, response_data: Dict[str, Any]):
        """记录响应日志"""
        self.logger.info("API Response", extra={"event_type": "api_response", "data": response_data})

    def log_agent_call(self, agent_type: str, input_data: Any, output_data: Any, tokens_used: int, latency_ms: float):
        """记录AI智能体调用日志"""
        self.logger.info(
            "Agent Call",
            extra={
                "event_type": "agent_call",
                "agent_type": agent_type,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "input_preview": str(input_data)[:100] if input_data else None,
                "output_preview": str(output_data)[:100] if output_data else None,
            },
        )

    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """记录安全事件"""
        self.logger.warning(
            "Security Event", extra={"event_type": "security", "security_event": event_type, "details": details}
        )

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """记录错误日志"""
        self.logger.error(
            "Application Error",
            extra={
                "event_type": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
            },
            exc_info=True,
        )

    def log_performance(self, operation: str, duration_ms: float, details: Optional[Dict[str, Any]] = None):
        """记录性能日志"""
        self.logger.info(
            "Performance Metric",
            extra={
                "event_type": "performance",
                "operation": operation,
                "duration_ms": duration_ms,
                "details": details or {},
            },
        )

    def log_business_event(
        self, event_name: str, user_id: str, session_id: str, details: Optional[Dict[str, Any]] = None
    ):
        """记录业务事件"""
        self.logger.info(
            "Business Event",
            extra={
                "event_type": "business",
                "event_name": event_name,
                "user_id": user_id,
                "session_id": session_id,
                "details": details or {},
            },
        )


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.counters = {}
        self.histograms = {}
        self.gauges = {}

    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self.counters[key] = self.counters.get(key, 0) + value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图数据"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        key = f"{name}:{json.dumps(labels, sort_keys=True) if labels else ''}"
        self.gauges[key] = value

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "counters": self.counters,
            "histograms": {
                key: {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
                for key, values in self.histograms.items()
            },
            "gauges": self.gauges,
        }


# 全局实例
structured_logger = StructuredLogger("salesboost")
metrics_collector = MetricsCollector()


def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)


def log_function_call(func_name: str, duration_ms: float, args_count: int = 0, result_type: Optional[str] = None):
    """记录函数调用"""
    structured_logger.log_performance(
        f"function_call:{func_name}", duration_ms, {"args_count": args_count, "result_type": result_type}
    )
    metrics_collector.record_histogram("function_duration", duration_ms, {"function": func_name})


# 装饰器：自动记录函数调用
def log_execution(logger: Optional[StructuredLogger] = None):
    """函数执行日志装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = f"{func.__module__}.{func.__qualname__}"

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                log_function_call(function_name, duration_ms, len(args) + len(kwargs), type(result).__name__)

                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                (logger or structured_logger).log_error(
                    e, {"function": function_name, "duration_ms": duration_ms, "args_count": len(args) + len(kwargs)}
                )
                raise

        return wrapper

    return decorator


# 导出主要类和函数
__all__ = [
    "StructuredLogger",
    "MetricsCollector",
    "get_logger",
    "log_function_call",
    "log_execution",
    "structured_logger",
    "metrics_collector",
]
