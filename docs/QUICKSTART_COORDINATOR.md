# 快速开始指南 - 任务编排系统改进

## 🚀 快速部署

### 1. 安装依赖

```bash
# 核心依赖
pip install prometheus-client celery redis numpy pydantic fastapi

# 可选依赖（高级功能）
pip install opentelemetry-api opentelemetry-sdk xgboost
```

### 2. 配置文件

创建 `config/workflow_config.json`:
```json
{
  "name": "production_workflow",
  "version": "1.0",
  "enabled_nodes": ["intent", "knowledge", "npc", "coach", "compliance"],
  "conditional_routing": {
    "intent": {
      "knowledge": "knowledge",
      "npc": "npc"
    }
  },
  "routing_rules": {
    "knowledge": ["npc"],
    "npc": ["coach"],
    "coach": ["compliance"]
  },
  "enable_reasoning": true,
  "enable_routing_policy": true,
  "enable_bandit": true,
  "bandit_exploration_rate": 0.1
}
```

### 3. 启动服务

```bash
# 终端1: 启动Redis
redis-server

# 终端2: 启动Celery Worker
celery -A app.tasks.coach_tasks worker --loglevel=info

# 终端3: 启动FastAPI应用
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 验证部署

```bash
# 测试用户反馈API
curl -X POST http://localhost:8000/api/v1/feedback/submit \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_123",
    "turn_number": 1,
    "rating": 5,
    "intent": "greeting"
  }'

# 查看Prometheus metrics
curl http://localhost:8000/metrics
```

---

## 📊 监控配置

### Prometheus配置

创建 `config/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'salesboost'
    static_configs:
      - targets: ['localhost:8000']
```

启动Prometheus:
```bash
prometheus --config.file=config/prometheus.yml
```

访问: http://localhost:9090

### Grafana Dashboard

1. 添加Prometheus数据源
2. 导入预定义查询:

```promql
# TTFT P95
histogram_quantile(0.95, rate(coordinator_turn_ttft_seconds_bucket[5m]))

# 节点成功率
rate(coordinator_node_execution_total{status="ok"}[5m]) / rate(coordinator_node_execution_total[5m])

# 用户满意度
avg(coordinator_user_satisfaction_score)

# Bandit arm性能
coordinator_bandit_arm_score
```

---

## 🔧 使用示例

### 1. 基本对话流程

```python
from app.engine.coordinator.production_coordinator import get_production_coordinator
from app.infra.gateway.model_gateway import ModelGateway
from app.infra.budget.budget_manager import BudgetManager

# 初始化
coordinator = get_production_coordinator(
    model_gateway=ModelGateway(),
    budget_manager=BudgetManager(),
    persona={"name": "张经理", "role": "采购经理"}
)

coordinator.initialize_session("session_123", "user_456")

# 执行对话
result = await coordinator.execute_turn(
    turn_number=1,
    user_message="你好",
    enable_async_coach=True  # TTFT优化
)

print(f"NPC回复: {result.npc_response}")
print(f"意图: {result.intent}")
print(f"TTFT: {result.ttft_ms}ms")
```

### 2. 收集用户反馈

```python
from api.endpoints.user_feedback import submit_feedback, UserFeedbackRequest

# 用户评分
await submit_feedback(UserFeedbackRequest(
    session_id="session_123",
    turn_number=1,
    rating=5,
    intent="greeting",
    decision_id=result.bandit_decision.get("decision_id"),
    signals={
        "response_quality": 0.9,
        "latency_satisfaction": 0.8
    }
))
```

### 3. 配置热更新

```python
from app.config.unified_config import get_config_manager
from app.engine.coordinator.dynamic_workflow import WorkflowConfig, NodeType

manager = await get_config_manager()

# 更新配置
new_config = WorkflowConfig(
    name="experiment_workflow",
    version="2.0",
    enabled_nodes={NodeType.INTENT, NodeType.NPC, NodeType.COACH},
    enable_bandit=True,
    bandit_exploration_rate=0.2  # 增加探索率
)

await manager.update_config(new_config, persist=True)

# 配置会自动应用到新的对话
```

### 4. 使用LinUCB Bandit

```python
from app.engine.coordinator.bandit_linucb import LinUCBBandit

bandit = LinUCBBandit(
    arms=["npc", "tools", "knowledge"],
    context_dim=10,
    alpha=0.5
)

# 决策
context = {
    "intent": "price_inquiry",
    "confidence": 0.9,
    "fsm_stage": "negotiation",
    "need_tools": True,
    "risk_flags": [],
    "recent_tool_calls": False
}

decision = bandit.choose(context)
print(f"选择: {decision['chosen']}")
print(f"UCB分数: {decision['ucb']:.3f}")
print(f"是否探索: {decision['exploration']}")

# 记录反馈
bandit.record_feedback(
    decision_id=decision["decision_id"],
    reward=0.8  # 来自用户评分
)

# 查看统计
stats = bandit.get_stats()
for arm, stat in stats.items():
    print(f"{arm}: pulls={stat['pulls']}, avg_reward={stat['avg_reward']:.3f}")
```

### 5. Reasoning Memory

```python
from app.engine.coordinator.reasoning_memory import get_reasoning_memory

memory = get_reasoning_memory()

# 存储推理
memory.add(
    session_id="session_123",
    turn_number=1,
    reasoning={
        "analysis": ["User is greeting"],
        "core_concern": "establish rapport",
        "strategy": "friendly response"
    },
    intent="greeting",
    confidence=0.95
)

# 获取上下文
context = memory.get_context_summary("session_123")
print(context)
# 输出: "Previous reasoning history:\n1. Turn 1 (greeting): Concern='establish rapport', Strategy='friendly response'"

# 查找相似情况
similar = memory.get_similar_situations(
    session_id="session_123",
    current_intent="price_inquiry",
    n=2
)
```

---

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/integration/test_coordinator_e2e.py -v

# 运行特定测试
pytest tests/integration/test_coordinator_e2e.py::TestBasicConversationFlow::test_single_turn_greeting -v

# 生成覆盖率报告
pytest tests/integration/test_coordinator_e2e.py --cov=app.engine.coordinator --cov-report=html
```

---

## 📈 性能优化

### 1. Redis连接池

```python
# core/redis.py
from redis import ConnectionPool, Redis

pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    decode_responses=True
)

def get_redis_sync():
    return Redis(connection_pool=pool)
```

### 2. Celery并发

```bash
# 使用prefork pool，4个worker进程
celery -A app.tasks.coach_tasks worker \
  --concurrency=4 \
  --pool=prefork \
  --max-tasks-per-child=1000 \
  --loglevel=info
```

### 3. 批量处理

```python
# 批量生成coach advice
from app.tasks.coach_tasks import batch_generate_coach_advice

tasks = [
    {
        "session_id": f"session_{i}",
        "turn_number": 1,
        "user_message": "你好",
        "npc_response": "您好！",
        "history": []
    }
    for i in range(100)
]

result = batch_generate_coach_advice.delay(tasks)
```

---

## 🔍 故障排查

### 问题1: Celery任务不执行

**检查**:
```bash
# 查看Celery worker状态
celery -A app.tasks.coach_tasks inspect active

# 查看队列
celery -A app.tasks.coach_tasks inspect reserved
```

**解决**:
- 确保Redis正在运行
- 检查Celery worker日志
- 验证任务序列化配置

### 问题2: Prometheus metrics不显示

**检查**:
```bash
# 访问metrics端点
curl http://localhost:8000/metrics | grep coordinator
```

**解决**:
- 确保已导入metrics模块
- 检查FastAPI应用是否暴露/metrics端点
- 验证Prometheus scrape配置

### 问题3: 配置热更新不生效

**检查**:
```python
from app.config.unified_config import get_config_manager

manager = await get_config_manager()
metadata = manager.get_metadata()
print(f"配置来源: {metadata.source}")
print(f"加载时间: {metadata.loaded_at}")
```

**解决**:
- 检查Redis连接
- 验证配置文件格式
- 查看auto_reload是否启用

---

## 📚 进阶功能

### 1. 自定义Metrics

```python
from prometheus_client import Counter

custom_metric = Counter(
    'my_custom_metric',
    'Description',
    ['label1', 'label2']
)

custom_metric.labels(label1='value1', label2='value2').inc()
```

### 2. 自定义Bandit特征

```python
class CustomLinUCBBandit(LinUCBBandit):
    def _context_to_features(self, context):
        features = []

        # 添加自定义特征
        features.append(context.get('custom_feature_1', 0.0))
        features.append(context.get('custom_feature_2', 0.0))

        # ... 其他特征

        while len(features) < self.context_dim:
            features.append(0.0)

        return np.array(features[:self.context_dim]).reshape(-1, 1)
```

### 3. 配置变更监听

```python
from app.config.unified_config import get_config_manager

manager = await get_config_manager()

# 注册监听器
def on_config_change(config):
    print(f"配置已更新: {config.name} v{config.version}")
    # 重新初始化coordinator
    reinitialize_coordinator(config)

manager.on_config_change(on_config_change)
```

---

## 🎯 最佳实践

1. **监控告警**: 设置Prometheus告警规则，监控TTFT、用户满意度、合规风险
2. **A/B测试**: 使用不同配置进行A/B测试，收集数据对比效果
3. **定期备份**: 定期备份Redis数据和配置文件
4. **日志分析**: 使用ELK stack分析coordinator日志
5. **性能调优**: 根据metrics数据调整bandit探索率、配置节点组合

---

## 📞 支持

- 文档: [COORDINATOR_IMPROVEMENTS_IMPLEMENTATION.md](COORDINATOR_IMPROVEMENTS_IMPLEMENTATION.md)
- 问题反馈: GitHub Issues
- 技术支持: tech-support@salesboost.com

---

**祝您使用愉快！** 🎉
