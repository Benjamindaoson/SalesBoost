"""
Prometheus Metrics API Endpoint
Exposes /metrics endpoint for Prometheus scraping
"""
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from app.observability.prometheus_exporter import get_intent_metrics_exporter

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", response_class=Response)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    返回Prometheus文本格式的指标数据，供Prometheus Server抓取

    Prometheus配置示例 (prometheus.yml):
    ```yaml
    scrape_configs:
      - job_name: 'salesboost'
        scrape_interval: 15s
        static_configs:
          - targets: ['localhost:8000']
    ```

    指标列表:
    - intent_classification_total: 意图分类总次数
    - intent_classification_success_total: 成功次数
    - intent_classification_errors_total: 错误次数
    - intent_classification_duration_seconds: 耗时分布（直方图）
    - intent_classification_confidence: 置信度分布（直方图）
    - intent_context_window_size: 上下文窗口大小
    - intent_fallback_to_rules_total: 降级到规则引擎次数
    - intent_context_aware_enhancements_total: 上下文增强次数
    - intent_model_info: 模型信息

    Returns:
        Response: Prometheus文本格式 (text/plain)
    """
    exporter = get_intent_metrics_exporter()
    metrics_data = exporter.get_metrics()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/metrics/debug/recent")
async def get_recent_classifications(limit: int = 100):
    """
    调试接口：获取最近的分类记录

    Args:
        limit: 返回的最大记录数（默认100）

    Returns:
        最近的分类记录列表
    """
    exporter = get_intent_metrics_exporter()
    recent = exporter.get_recent_classifications(limit=limit)

    return {
        "total": len(recent),
        "classifications": recent
    }
