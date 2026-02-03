# Intent Recognition Monitoring Setup Guide

## 概述

本文档介绍如何配置和使用意图识别专项监控系统（Prometheus + Grafana）。

## 架构

```
Intent Classifier
    ↓ (自动记录指标)
Prometheus Exporter (app/observability/prometheus_exporter.py)
    ↓ (暴露 /metrics)
Prometheus Server (抓取指标)
    ↓ (数据存储)
Grafana (可视化仪表盘)
```

## 1. Prometheus导出器集成

### 1.1 自动监控（装饰器方式）

已集成到 `ContextAwareIntentClassifier.classify_with_context()` 方法：

```python
from app.observability.prometheus_exporter import monitor_intent_classification

@monitor_intent_classification
async def classify_with_context(self, message: str, history: list, fsm_state: dict):
    # 分类逻辑
    return IntentResult(intent='greeting', confidence=0.95)
```

**自动收集的指标**:
- 分类耗时
- 成功/失败状态
- 意图类型
- 置信度
- 上下文窗口大小

### 1.2 手动记录指标

```python
from app.observability.prometheus_exporter import get_intent_metrics_exporter

exporter = get_intent_metrics_exporter()

# 记录单次分类
exporter.record_classification(
    intent='price_inquiry',
    confidence=0.92,
    duration_ms=45.2,
    model_type='fasttext',
    context_size=5,
    session_id='session_123',
    success=True
)

# 记录降级事件
exporter.record_fallback(reason='low_confidence')

# 记录上下文增强
exporter.record_context_enhancement(enhancement_type='pattern_adjustment')
```

## 2. API端点配置

### 2.1 添加到FastAPI应用

在 `main.py` 中注册监控路由：

```python
from fastapi import FastAPI
from api.endpoints.monitoring import router as monitoring_router

app = FastAPI()

# 注册监控端点
app.include_router(
    monitoring_router,
    prefix="",  # /metrics 直接在根路径
    tags=["monitoring"]
)
```

### 2.2 验证端点

启动应用后访问：

```bash
# Prometheus指标端点
curl http://localhost:8000/metrics

# 调试端点（最近100条分类记录）
curl http://localhost:8000/metrics/debug/recent?limit=100
```

**预期输出** (`/metrics`):
```
# HELP intent_classification_total Total number of intent classifications
# TYPE intent_classification_total counter
intent_classification_total{intent="greeting",model_type="fasttext",source="production"} 1234.0

# HELP intent_classification_duration_seconds Intent classification latency in seconds
# TYPE intent_classification_duration_seconds histogram
intent_classification_duration_seconds_bucket{intent="greeting",model_type="fasttext",le="0.01"} 0.0
intent_classification_duration_seconds_bucket{intent="greeting",model_type="fasttext",le="0.025"} 512.0
...
```

## 3. Prometheus Server配置

### 3.1 安装Prometheus

```bash
# Docker方式
docker run -d --name prometheus -p 9090:9090 \
  -v $(pwd)/config/prometheus:/etc/prometheus \
  prom/prometheus

# 或下载二进制
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
```

### 3.2 配置抓取任务

创建 `config/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s      # 每15秒抓取一次
  evaluation_interval: 15s  # 每15秒评估一次规则

scrape_configs:
  - job_name: 'salesboost-intent'
    static_configs:
      - targets: ['localhost:8000']  # SalesBoost应用地址
        labels:
          app: 'salesboost'
          component: 'intent-classifier'

    # 健康检查
    scrape_timeout: 10s
    metrics_path: '/metrics'
```

### 3.3 启动Prometheus

```bash
./prometheus --config.file=config/prometheus/prometheus.yml
```

访问 http://localhost:9090 验证：

- Status → Targets：应该看到 `salesboost-intent` 状态为 `UP`
- Graph：查询 `intent_classification_total` 应该有数据

## 4. Grafana仪表盘配置

### 4.1 安装Grafana

```bash
# Docker方式
docker run -d --name=grafana -p 3000:3000 grafana/grafana

# 或下载二进制
wget https://dl.grafana.com/oss/release/grafana-10.2.0.linux-amd64.tar.gz
tar -zxvf grafana-*.tar.gz
cd grafana-*
./bin/grafana-server
```

### 4.2 添加Prometheus数据源

1. 访问 http://localhost:3000 (默认登录: admin/admin)
2. Configuration → Data Sources → Add data source
3. 选择 **Prometheus**
4. 配置:
   - Name: `Prometheus`
   - URL: `http://localhost:9090`
   - Scrape interval: `15s`
5. 点击 **Save & Test**

### 4.3 导入仪表盘模板

1. Dashboards → Import
2. 上传文件: `config/grafana/intent_dashboard.json`
3. 选择数据源: `Prometheus`
4. 点击 **Import**

**仪表盘包含11个面板**:

| 面板 | 指标 | 用途 |
|-----|------|------|
| 1. Intent Classification Rate | `rate(intent_classification_total[1m])` | 每秒分类请求数 |
| 2. Success Rate | `success / total * 100` | 成功率百分比 |
| 3. Latency (P50/P95/P99) | `histogram_quantile` | 延迟分位数 |
| 4. Intent Distribution | `topk(10, sum by (intent))` | Top 10意图类型 |
| 5. Average Confidence | `avg(intent_classification_confidence)` | 平均置信度 |
| 6. Fallback Rate | `rate(intent_fallback_to_rules_total)` | 降级频率 |
| 7. Classification Errors | `increase(errors[5m])` | 最近5分钟错误数 |
| 8. Confidence Distribution | `histogram_quantile` | 置信度分位数 |
| 9. Context Enhancements | `rate(enhancements[1m])` | 上下文增强频率 |
| 10. Summary Table | `increase(total[5m])` | 最近5分钟汇总 |
| 11. Model Info | `intent_model_info` | 模型元信息 |

## 5. 告警配置（可选）

### 5.1 Prometheus告警规则

创建 `config/prometheus/alerts.yml`:

```yaml
groups:
  - name: intent_classification
    interval: 30s
    rules:
      # 成功率低于90%
      - alert: IntentClassificationLowSuccessRate
        expr: |
          (rate(intent_classification_success_total[5m]) /
           rate(intent_classification_total[5m])) < 0.9
        for: 5m
        labels:
          severity: warning
          component: intent-classifier
        annotations:
          summary: "Intent classification success rate below 90%"
          description: "Success rate is {{ $value | humanizePercentage }}"

      # P99延迟超过200ms
      - alert: IntentClassificationHighLatency
        expr: |
          histogram_quantile(0.99,
            rate(intent_classification_duration_seconds_bucket[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
          component: intent-classifier
        annotations:
          summary: "Intent classification P99 latency > 200ms"
          description: "P99 latency is {{ $value }}s"

      # 降级频率过高
      - alert: IntentClassificationHighFallbackRate
        expr: |
          rate(intent_fallback_to_rules_total[5m]) > 10
        for: 5m
        labels:
          severity: info
          component: intent-classifier
        annotations:
          summary: "High fallback to rule engine rate"
          description: "Fallback rate is {{ $value }} req/s"
```

更新 `prometheus.yml`:

```yaml
rule_files:
  - "alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']  # Alertmanager地址
```

## 6. 验证监控系统

### 6.1 功能测试

```bash
# 1. 启动SalesBoost应用
python main.py

# 2. 触发一些意图分类请求（通过WebSocket或API）

# 3. 检查Prometheus指标
curl http://localhost:8000/metrics | grep intent_classification

# 4. 在Prometheus UI查询
# 访问 http://localhost:9090/graph
# 查询: rate(intent_classification_total[1m])

# 5. 在Grafana查看仪表盘
# 访问 http://localhost:3000
# 进入 "SalesBoost Intent Recognition Monitoring" 仪表盘
```

### 6.2 性能基准

**目标指标**:

| 指标 | 目标值 | 告警阈值 |
|-----|--------|---------|
| 成功率 | > 95% | < 90% |
| P50延迟 | < 30ms | - |
| P95延迟 | < 50ms | - |
| P99延迟 | < 100ms | > 200ms |
| 降级率 | < 5% | > 20% |
| 平均置信度 | > 0.8 | < 0.6 |

## 7. 故障排查

### 7.1 指标未上报

**症状**: `/metrics` 端点返回空或没有 `intent_classification_*` 指标

**检查**:
```python
# 验证装饰器已应用
from app.engine.intent.context_aware_classifier import ContextAwareIntentClassifier
import inspect
classifier = ContextAwareIntentClassifier()
print(inspect.getsource(classifier.classify_with_context))
# 应该看到 @monitor_intent_classification
```

**解决**: 确保分类器被实际调用过（至少一次）

### 7.2 Prometheus无法抓取

**症状**: Prometheus Targets显示 `DOWN`

**检查**:
```bash
# 测试端点可访问性
curl -I http://localhost:8000/metrics

# 检查Prometheus日志
docker logs prometheus | grep salesboost
```

**解决**:
- 确认SalesBoost应用正在运行
- 检查防火墙规则
- 验证 `prometheus.yml` 中的 `targets` 地址正确

### 7.3 Grafana仪表盘无数据

**症状**: 所有面板显示 "No data"

**检查**:
```bash
# 在Grafana Explore中测试查询
# Query: intent_classification_total

# 在Prometheus UI中验证数据
curl http://localhost:9090/api/v1/query?query=intent_classification_total
```

**解决**:
- 确认Prometheus数据源连接成功
- 检查时间范围（默认Last 6h）
- 验证至少有一次分类请求

## 8. 集成到CI/CD

### 8.1 监控健康检查

```bash
#!/bin/bash
# scripts/check_metrics_health.sh

# 检查/metrics端点
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/metrics)

if [ "$response" != "200" ]; then
  echo "FAIL: Metrics endpoint not responding"
  exit 1
fi

# 检查是否有intent指标
metrics=$(curl -s http://localhost:8000/metrics | grep -c "intent_classification_total")

if [ "$metrics" -eq "0" ]; then
  echo "FAIL: No intent metrics found"
  exit 1
fi

echo "PASS: Metrics endpoint healthy"
exit 0
```

### 8.2 性能回归测试

```python
# tests/integration/test_metrics_performance.py
import pytest
import time
from app.engine.intent.context_aware_classifier import ContextAwareIntentClassifier
from app.observability.prometheus_exporter import get_intent_metrics_exporter

@pytest.mark.asyncio
async def test_classification_latency_sla():
    """验证P95延迟 < 50ms"""
    classifier = ContextAwareIntentClassifier()
    exporter = get_intent_metrics_exporter()

    # 执行100次分类
    for i in range(100):
        await classifier.classify_with_context(
            message="测试消息",
            history=[],
            fsm_state={"current_stage": "discovery", "turn_count": 1}
        )

    # 获取最近分类记录
    recent = exporter.get_recent_classifications(limit=100)
    latencies = [r['duration_ms'] for r in recent]

    # 计算P95
    latencies_sorted = sorted(latencies)
    p95_index = int(0.95 * len(latencies_sorted))
    p95_latency = latencies_sorted[p95_index]

    assert p95_latency < 50, f"P95 latency {p95_latency}ms exceeds 50ms SLA"
```

## 9. 总结

### 已完成组件

- ✅ **Prometheus Exporter** (`app/observability/prometheus_exporter.py`)
  - 11个指标定义
  - 自动监控装饰器
  - 手动记录API

- ✅ **API端点** (`api/endpoints/monitoring.py`)
  - `/metrics` - Prometheus抓取端点
  - `/metrics/debug/recent` - 调试端点

- ✅ **Grafana仪表盘** (`config/grafana/intent_dashboard.json`)
  - 11个可视化面板
  - 变量过滤（intent, model_type）
  - 实时刷新（30s）

- ✅ **集成到分类器**
  - `ContextAwareIntentClassifier.classify_with_context()` 已添加装饰器

### 下一步行动

1. **部署Prometheus Server**
   ```bash
   docker run -d -p 9090:9090 -v $(pwd)/config/prometheus:/etc/prometheus prom/prometheus
   ```

2. **部署Grafana**
   ```bash
   docker run -d -p 3000:3000 grafana/grafana
   ```

3. **导入仪表盘**
   - 访问 http://localhost:3000
   - Import → `config/grafana/intent_dashboard.json`

4. **验证数据流**
   - SalesBoost应用 → `/metrics` → Prometheus → Grafana

5. **配置告警**（可选）
   - 添加 `alerts.yml`
   - 配置Alertmanager

---

**文档完成** | **系统就绪** | **监控上线** ✅
