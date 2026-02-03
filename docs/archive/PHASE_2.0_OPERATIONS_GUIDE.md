# Phase 2.0: 运营部署指南

## 执行摘要

Phase 1.5完成了代码集成，Phase 2.0专注于**安全生产部署**和**持续监控**。

---

## 🚀 动作1: 灰度切换 (Feature Flag)

### 实施完成

✅ 创建了特性开关系统：
- [app/config/feature_flags.py](app/config/feature_flags.py) - 特性开关核心
- [.env.feature_flags.example](.env.feature_flags.example) - 配置模板

### 使用指南

#### 1. 创建配置文件

```bash
cp .env.feature_flags.example .env
```

#### 2. 选择编排引擎

**当前状态（安全）**:
```bash
# .env
COORDINATOR_ENGINE=legacy
ENABLE_ML_INTENT=false
```

**Canary测试（10%流量）**:
```bash
# .env
COORDINATOR_ENGINE=workflow
ENABLE_ML_INTENT=true
ENABLE_CONTEXT_AWARE=true
AB_TESTING_ENABLED=true
AB_TRAFFIC_SPLIT=0.1
```

**完全迁移到LangGraph**:
```bash
# .env
COORDINATOR_ENGINE=langgraph
ENABLE_ML_INTENT=true
ENABLE_CONTEXT_AWARE=true
AB_TESTING_ENABLED=false
```

#### 3. 在应用中集成

**主入口文件修改建议** (`api/endpoints/websocket.py` 或 `main.py`):

```python
from app.config.feature_flags import FeatureFlags, CoordinatorEngine

# Get configured engine
engine = FeatureFlags.get_coordinator_engine()

if engine == CoordinatorEngine.LANGGRAPH:
    from app.engine.coordinator.langgraph_coordinator import LangGraphCoordinator
    coordinator = LangGraphCoordinator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        persona=persona_data
    )
    logger.info("Using LangGraph coordinator (graph-oriented)")

elif engine == CoordinatorEngine.WORKFLOW:
    from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator
    coordinator = WorkflowCoordinator(
        model_gateway=model_gateway,
        budget_manager=budget_manager,
        session_director=session_director,
        persona=persona_data
    )
    logger.info("Using WorkflowCoordinator (linear + AI intent)")

else:  # LEGACY
    from cognitive import Orchestrator
    coordinator = Orchestrator(model_caller=model_gateway)
    logger.info("Using legacy Orchestrator (MVP)")
```

### 推荐迁移路径

```
Week 1: Legacy (100%)           → Collect baseline metrics
Week 2: Workflow (10% A/B)      → Compare ML intent vs legacy
Week 3: Workflow (50% A/B)      → Gradual rollout
Week 4: Workflow (100%)         → Full migration to AI intent
Week 5: LangGraph (10% A/B)     → Test graph-oriented flow
Week 6: LangGraph (100%)        → Complete migration
```

---

## 📊 动作2: 点亮仪表盘

### 实施完成

✅ 创建了性能监控系统：
- [app/observability/metrics_exporter.py](app/observability/metrics_exporter.py) - 指标导出器
- [scripts/view_metrics_dashboard.py](scripts/view_metrics_dashboard.py) - 简易仪表盘

### 启用监控

#### 1. 在应用启动时启动导出器

**修改 `main.py`**:

```python
from app.observability.metrics_exporter import start_metrics_export, stop_metrics_export

@app.on_event("startup")
async def startup():
    # Start background metrics export
    start_metrics_export()
    logger.info("Metrics exporter started")

@app.on_event("shutdown")
async def shutdown():
    # Stop metrics export
    stop_metrics_export()
    logger.info("Metrics exporter stopped")
```

#### 2. 查看实时仪表盘

```bash
# 查看最近24小时的指标
python scripts/view_metrics_dashboard.py
```

**输出示例**:
```
📊 SALESBOOST METRICS DASHBOARD (Last 24h)
================================================================================

📈 intent.classify
   Total Requests: 1,234
   Success Rate:   98.5%
   Latency (avg):
     Mean: 45.2ms
     P95:  78.5ms
     P99:  112.3ms
   Status: ✅ Healthy

📈 npc.generate
   Total Requests: 1,234
   Success Rate:   97.2%
   Latency (avg):
     Mean: 1,234.5ms
     P95:  2,456.7ms
     P99:  3,102.1ms
   Status: ⚠️  Warning (P99 > 2s)
```

#### 3. 集成到Grafana/Prometheus（可选）

**指标文件位置**: `logs/metrics.jsonl`

**格式**: JSON Lines，每行一个快照
```json
{"timestamp": "2026-01-29T12:00:00", "components": {"intent.classify": {...}}}
```

**Prometheus导出器示例** (需自行实现):
```python
# 读取 logs/metrics.jsonl
# 转换为 Prometheus 格式
# 暴露 /metrics 端点
```

---

## 🧹 动作3: 扫除战场

### 已完成

✅ **旧文件清理状态**:
- `app/engine/intent/intent_classifier.py` - ✅ 已删除（UPGRADE_REPORT.md第152行确认）
- 所有依赖已更新到新分类器

### 依赖检查

确认没有任何代码仍在引用旧文件：

```bash
# 搜索是否有残留引用
grep -r "from app.engine.intent.intent_classifier import" app/
grep -r "IntentGateway" app/ --include="*.py"
```

**当前状态**: ✅ 所有旧引用已清理（见Phase 1.5报告）

---

## 📋 部署检查清单

### 部署前

- [ ] 复制 `.env.feature_flags.example` 为 `.env`
- [ ] 设置 `COORDINATOR_ENGINE=legacy`（安全起见）
- [ ] 启用 `PERFORMANCE_MONITORING=true`
- [ ] 确认 `logs/` 目录有写权限

### 代码集成

- [ ] 在 `main.py` 添加特性开关逻辑
- [ ] 在 `app.on_event("startup")` 启动 metrics_exporter
- [ ] 在 `app.on_event("shutdown")` 停止 metrics_exporter
- [ ] 测试各引擎切换（legacy/workflow/langgraph）

### Canary测试

- [ ] 设置 `AB_TESTING_ENABLED=true`
- [ ] 设置 `AB_TRAFFIC_SPLIT=0.1`（10%流量）
- [ ] 运行24小时收集数据
- [ ] 对比 `logs/ab_test_metrics.jsonl` 中两个变体的表现

### 监控验证

- [ ] 确认 `logs/metrics.jsonl` 正在生成
- [ ] 运行 `python scripts/view_metrics_dashboard.py` 查看数据
- [ ] 检查意图分类准确率 > 80%
- [ ] 检查P99延迟 < 200ms（intent）、< 3s（npc）

### 完全迁移

- [ ] 将 `AB_TRAFFIC_SPLIT` 逐步提升到 0.5 → 1.0
- [ ] 设置 `COORDINATOR_ENGINE=workflow`
- [ ] 监控1周，确认稳定
- [ ] （可选）切换到 `COORDINATOR_ENGINE=langgraph`

---

## 🚨 回滚计划

如果新引擎出现问题，立即回滚：

```bash
# 1. 修改 .env
COORDINATOR_ENGINE=legacy

# 2. 重启应用
# 无需代码变更，环境变量即时生效

# 3. 监控回滚后的表现
python scripts/view_metrics_dashboard.py
```

---

## 📈 成功指标

部署成功的标志：

| 指标 | 目标 | 验证方式 |
|-----|------|---------|
| 意图识别准确率 | > 80% | `logs/metrics.jsonl` |
| P99延迟（intent） | < 200ms | Dashboard |
| P99延迟（npc） | < 3s | Dashboard |
| 成功率 | > 95% | Dashboard |
| 无回滚 | 7天稳定运行 | 生产日志 |

---

## 📞 支持

如有问题：

1. 检查 `logs/metrics.jsonl` 是否正常生成
2. 查看应用日志中的 `[MetricsExporter]` 条目
3. 确认 `.env` 配置正确
4. 运行 `python scripts/quick_fasttext_test.py` 验证ML模型

---

## ✨ 总结

Phase 2.0 实施了：

✅ **特性开关系统** - 安全切换引擎，无需重新部署
✅ **性能监控** - 实时追踪P50/P95/P99延迟和成功率
✅ **简易仪表盘** - 快速查看系统健康状态
✅ **代码清理** - 移除所有旧Mock实现

**系统现在支持零停机、可观测、可回滚的生产部署。**

下一步：执行Canary测试，逐步迁移流量到新引擎。
