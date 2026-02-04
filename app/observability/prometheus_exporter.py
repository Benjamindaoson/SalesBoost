"""
Prometheus Metrics Exporter for Intent Recognition
Exposes intent classification metrics in Prometheus format
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import Response

logger = logging.getLogger(__name__)


class IntentMetricsExporter:
    """
    Intent Recognition专项监控 - Prometheus导出器

    暴露以下指标：
    - intent_classification_total: 意图分类总次数（按intent标签）
    - intent_classification_duration_seconds: 分类耗时直方图
    - intent_classification_confidence: 置信度分布
    - intent_classification_errors_total: 分类错误计数
    - intent_context_window_size: 上下文窗口大小
    - intent_fallback_total: 降级到规则引擎的次数
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Args:
            registry: Prometheus registry（默认使用全局registry）
        """
        self.registry = registry or CollectorRegistry()

        # 指标定义
        self._define_metrics()

        # 缓存最近的指标数据
        self._recent_classifications: List[Dict] = []
        self._max_cache_size = 1000

        logger.info("[PrometheusExporter] Intent metrics exporter initialized")

    def _define_metrics(self):
        """定义Prometheus指标"""

        # Counter: 意图分类总次数（按intent类型分组）
        self.intent_total = Counter(
            name='intent_classification_total',
            documentation='Total number of intent classifications',
            labelnames=['intent', 'model_type', 'source'],
            registry=self.registry
        )

        # Counter: 分类成功次数
        self.intent_success = Counter(
            name='intent_classification_success_total',
            documentation='Number of successful intent classifications',
            labelnames=['intent', 'model_type'],
            registry=self.registry
        )

        # Counter: 分类失败次数
        self.intent_errors = Counter(
            name='intent_classification_errors_total',
            documentation='Number of failed intent classifications',
            labelnames=['error_type', 'model_type'],
            registry=self.registry
        )

        # Histogram: 分类耗时（毫秒）
        self.intent_duration = Histogram(
            name='intent_classification_duration_seconds',
            documentation='Intent classification latency in seconds',
            labelnames=['intent', 'model_type'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )

        # Histogram: 置信度分布
        self.intent_confidence = Histogram(
            name='intent_classification_confidence',
            documentation='Intent classification confidence score',
            labelnames=['intent', 'model_type'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
            registry=self.registry
        )

        # Gauge: 当前上下文窗口大小
        self.context_window_size = Gauge(
            name='intent_context_window_size',
            documentation='Current context window size for intent classification',
            labelnames=['session_id'],
            registry=self.registry
        )

        # Counter: 降级到规则引擎的次数
        self.fallback_total = Counter(
            name='intent_fallback_to_rules_total',
            documentation='Number of times ML model fell back to rule-based engine',
            labelnames=['reason'],
            registry=self.registry
        )

        # Counter: 上下文感知增强触发次数
        self.context_aware_total = Counter(
            name='intent_context_aware_enhancements_total',
            documentation='Number of context-aware enhancements applied',
            labelnames=['enhancement_type'],
            registry=self.registry
        )

        # Info: 模型信息
        self.model_info = Info(
            name='intent_model_info',
            documentation='Information about the intent classification model',
            registry=self.registry
        )

        # 设置模型信息
        self.model_info.info({
            'model_type': 'fasttext',
            'model_version': '1.0',
            'context_aware': 'true',
            'rule_fallback': 'true'
        })

    def record_classification(
        self,
        intent: str,
        confidence: float,
        duration_ms: float,
        model_type: str = 'fasttext',
        source: str = 'production',
        context_size: int = 0,
        session_id: str = 'default',
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """
        记录单次分类事件

        Args:
            intent: 识别的意图
            confidence: 置信度 (0-1)
            duration_ms: 耗时（毫秒）
            model_type: 模型类型 (fasttext/rule/hybrid)
            source: 来源 (production/ab_test/canary)
            context_size: 上下文消息数量
            session_id: 会话ID
            success: 是否成功
            error_type: 错误类型（如失败）
        """
        try:
            # 记录总次数
            self.intent_total.labels(
                intent=intent,
                model_type=model_type,
                source=source
            ).inc()

            if success:
                # 记录成功
                self.intent_success.labels(
                    intent=intent,
                    model_type=model_type
                ).inc()

                # 记录耗时
                self.intent_duration.labels(
                    intent=intent,
                    model_type=model_type
                ).observe(duration_ms / 1000.0)  # 转换为秒

                # 记录置信度
                self.intent_confidence.labels(
                    intent=intent,
                    model_type=model_type
                ).observe(confidence)

                # 更新上下文窗口大小
                if context_size > 0:
                    self.context_window_size.labels(
                        session_id=session_id
                    ).set(context_size)

            else:
                # 记录错误
                self.intent_errors.labels(
                    error_type=error_type or 'unknown',
                    model_type=model_type
                ).inc()

            # 缓存最近的分类（用于调试）
            self._recent_classifications.append({
                'timestamp': datetime.utcnow().isoformat(),
                'intent': intent,
                'confidence': confidence,
                'duration_ms': duration_ms,
                'model_type': model_type,
                'success': success
            })

            # 限制缓存大小
            if len(self._recent_classifications) > self._max_cache_size:
                self._recent_classifications.pop(0)

        except Exception as e:
            logger.error(f"[PrometheusExporter] Failed to record classification: {e}")

    def record_fallback(self, reason: str = 'low_confidence'):
        """记录降级到规则引擎的事件"""
        try:
            self.fallback_total.labels(reason=reason).inc()
        except Exception as e:
            logger.error(f"[PrometheusExporter] Failed to record fallback: {e}")

    def record_context_enhancement(self, enhancement_type: str):
        """记录上下文感知增强事件"""
        try:
            self.context_aware_total.labels(
                enhancement_type=enhancement_type
            ).inc()
        except Exception as e:
            logger.error(f"[PrometheusExporter] Failed to record enhancement: {e}")

    def get_metrics(self) -> bytes:
        """
        获取Prometheus格式的指标数据

        Returns:
            bytes: Prometheus文本格式的指标
        """
        return generate_latest(self.registry)

    def get_recent_classifications(self, limit: int = 100) -> List[Dict]:
        """
        获取最近的分类记录（用于调试）

        Args:
            limit: 返回的最大记录数

        Returns:
            最近的分类记录列表
        """
        return self._recent_classifications[-limit:]


# 全局单例
_intent_metrics_exporter: Optional[IntentMetricsExporter] = None


def get_intent_metrics_exporter() -> IntentMetricsExporter:
    """获取全局Intent指标导出器"""
    global _intent_metrics_exporter

    if _intent_metrics_exporter is None:
        _intent_metrics_exporter = IntentMetricsExporter()

    return _intent_metrics_exporter


def create_prometheus_endpoint() -> Response:
    """
    FastAPI路由处理函数

    Usage:
        from fastapi import APIRouter
        from app.observability.prometheus_exporter import create_prometheus_endpoint

        router = APIRouter()

        @router.get("/metrics")
        async def metrics():
            return create_prometheus_endpoint()

    Returns:
        Prometheus格式的响应
    """
    exporter = get_intent_metrics_exporter()
    metrics_data = exporter.get_metrics()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


# ==================== 与IntentClassifier集成的装饰器 ====================

def monitor_intent_classification(func):
    """
    装饰器：自动监控意图分类函数

    Usage:
        @monitor_intent_classification
        async def classify(self, message: str, history: list):
            # your classification logic
            return IntentResult(intent='greeting', confidence=0.95)
    """
    import functools
    import time

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        exporter = get_intent_metrics_exporter()

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # 记录成功的分类
            exporter.record_classification(
                intent=result.intent,
                confidence=result.confidence,
                duration_ms=duration_ms,
                model_type=getattr(result, 'model_type', 'fasttext'),
                context_size=len(kwargs.get('history', [])),
                success=True
            )

            # 如果是降级
            if hasattr(result, 'is_fallback') and result.is_fallback:
                exporter.record_fallback(reason='low_confidence')

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # 记录失败的分类
            exporter.record_classification(
                intent='error',
                confidence=0.0,
                duration_ms=duration_ms,
                model_type='unknown',
                success=False,
                error_type=type(e).__name__
            )

            raise

    return wrapper
