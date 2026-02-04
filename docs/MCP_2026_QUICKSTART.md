# MCP 2026 快速开始指南

## 🚀 5分钟上手

### 前置要求

```bash
# Python 3.9+
python --version

# Redis (用于A2A)
redis-server --version

# 安装依赖
pip install redis pyyaml pytest pytest-asyncio
```

---

## 📦 运行演示

### 方式1: 完整演示（推荐）

```bash
# 运行2026年顶尖水平演示
python examples/mcp_2026_advanced_demo.py
```

**输出示例**:
```
======================================================================
MCP 2026: 硅谷顶尖水平演示
======================================================================

======================================================================
DEMO 1: 智能工具编排 (Intelligent Orchestration)
======================================================================

--- AI Planning ---
✓ Plan created with 3 tool calls
  Estimated cost: $0.030
  Estimated latency: 2.50s

--- Execution Order (2 batches) ---
Batch 1: ['knowledge_retriever', 'profile_reader']
Batch 2: ['price_calculator']

--- Executing Plan ---
✓ Execution succeeded
  Actual cost: $0.023
  Actual latency: 1.85s

...
```

### 方式2: 单独测试各组件

#### 测试智能编排器

```python
from app.mcp.orchestrator import MCPOrchestrator

orchestrator = MCPOrchestrator(registry, executor, llm_client)

plan = await orchestrator.plan(
    intent="research customer",
    context={"customer": "Acme Corp"}
)

result = await orchestrator.execute(plan)
```

#### 测试动态工具生成

```python
from app.mcp.dynamic_tools import DynamicToolGenerator

generator = DynamicToolGenerator()

tool = await generator.generate(
    template_id="roi_calculator",
    context={"industry": "SaaS", "avg_roi": 2.5}
)

result = await tool.execute(current_spend=200000, expected_improvement=0.30)
```

#### 测试服务网格

```python
from app.mcp.service_mesh import MCPMesh, RoutingStrategy

mesh = MCPMesh()
await mesh.start()

await mesh.register_node(
    node_id="node1",
    endpoint="http://localhost:8100",
    capabilities={"sales"}
)

result = await mesh.call_capability(
    capability="sales",
    method="generate_pitch",
    params={"customer": "Acme"}
)
```

---

## 🎯 实际应用示例

### 示例1: 智能客户研究

```python
import asyncio
from app.mcp.orchestrator import MCPOrchestrator
from app.tools.registry import build_default_registry
from app.tools.executor import ToolExecutor

async def research_customer(customer_name: str):
    """智能客户研究"""

    # 初始化
    registry = build_default_registry()
    executor = ToolExecutor(registry=registry)
    orchestrator = MCPOrchestrator(registry, executor, llm_client)

    # AI自动规划
    plan = await orchestrator.plan(
        intent=f"research {customer_name} comprehensively",
        context={"customer": customer_name},
        constraints={"max_cost": 0.50, "max_latency": 10.0}
    )

    # 执行
    result = await orchestrator.execute(plan)

    return result

# 使用
result = await research_customer("Acme Corp")
print(f"Research completed in {result.total_latency:.2f}s")
print(f"Cost: ${result.total_cost:.3f}")
```

### 示例2: 动态定价

```python
from app.mcp.dynamic_tools import DynamicToolGenerator

async def calculate_dynamic_price(customer_context: dict, base_price: float, quantity: int):
    """根据客户上下文动态定价"""

    generator = DynamicToolGenerator()

    # 生成定制化定价工具
    pricing_tool = await generator.generate(
        template_id="dynamic_pricer",
        context={
            "customer_tier": customer_context["tier"],
            "industry": customer_context["industry"],
            "relationship_score": customer_context["relationship_score"],
            "tier_discounts": {
                "startup": 0.05,
                "growth": 0.10,
                "enterprise": 0.20
            },
            "volume_discounts": {
                100: 0.05,
                500: 0.10,
                1000: 0.15
            }
        }
    )

    # 计算价格
    result = await pricing_tool.execute(
        base_price=base_price,
        quantity=quantity
    )

    return result["result"]

# 使用
customer = {
    "tier": "enterprise",
    "industry": "Finance",
    "relationship_score": 0.8
}

price = await calculate_dynamic_price(customer, 100, 1000)
print(f"Final price: ${price['final_price']:,.0f}")
print(f"Discount: {price['total_discount']:.1%}")
```

### 示例3: 多区域部署

```python
from app.mcp.service_mesh import MCPMesh, RoutingStrategy

async def setup_global_mesh():
    """设置全球服务网格"""

    mesh = MCPMesh(default_strategy=RoutingStrategy.WEIGHTED)
    await mesh.start()

    # 注册美国东部节点
    await mesh.register_node(
        node_id="us-east",
        name="US East",
        endpoint="http://us-east.salesboost.com:8100",
        capabilities={"sales", "crm", "knowledge"},
        cost_per_request=0.01,
        quality_score=0.95
    )

    # 注册美国西部节点
    await mesh.register_node(
        node_id="us-west",
        name="US West",
        endpoint="http://us-west.salesboost.com:8100",
        capabilities={"market_research", "data_enrichment"},
        cost_per_request=0.05,
        quality_score=0.90
    )

    # 注册欧洲节点
    await mesh.register_node(
        node_id="eu",
        name="Europe",
        endpoint="http://eu.salesboost.com:8100",
        capabilities={"sales", "crm"},
        cost_per_request=0.01,
        quality_score=0.85
    )

    return mesh

# 使用
mesh = await setup_global_mesh()

# 智能路由（自动选择最佳节点）
result = await mesh.call_capability(
    capability="market_research",
    method="research_company",
    params={"company": "Acme Corp"},
    strategy=RoutingStrategy.WEIGHTED  # 综合考虑延迟/成本/质量
)
```

---

## 🔧 配置

### 环境变量

```bash
# .env
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
MCP_DEFAULT_STRATEGY=weighted
MCP_MAX_PARALLEL_CALLS=5
MCP_HEALTH_CHECK_INTERVAL=30
```

### 配置文件

创建 `config/mcp_2026.yaml`:

```yaml
orchestrator:
  max_parallel_calls: 5
  default_timeout: 30.0
  enable_learning: true

dynamic_tools:
  enable_cache: true
  security_check: true

service_mesh:
  default_strategy: weighted
  health_check_interval: 30.0
  routing_weights:
    latency: 0.3
    load: 0.2
    cost: 0.2
    quality: 0.3
```

---

## 📊 监控

### 获取性能统计

```python
# 编排器统计
stats = orchestrator.get_performance_stats()
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Average cost: ${stats['average_cost']:.3f}")
print(f"Average latency: {stats['average_latency']:.2f}s")

# 网格状态
status = mesh.get_mesh_status()
print(f"Online nodes: {status['online_nodes']}/{status['total_nodes']}")
print(f"Total requests: {status['total_requests']}")
print(f"Success rate: {status['success_rate']:.1%}")
```

---

## 🐛 故障排查

### 问题1: 工具执行失败

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查工具注册
tools = registry.list_tools()
print(f"Available tools: {[t.name for t in tools]}")

# 测试单个工具
result = await executor.execute(
    name="knowledge_retriever",
    payload={"query": "test"},
    caller_role="test"
)
print(result)
```

### 问题2: 节点不可用

```python
# 检查节点状态
nodes = mesh.discover_nodes()
for node in nodes:
    print(f"{node.node_id}: {node.status}")
    print(f"  Load: {node.metrics.current_load}/{node.metrics.max_load}")
    print(f"  Success rate: {node.metrics.success_rate:.1%}")

# 手动健康检查
await mesh._health_check()
```

### 问题3: 成本过高

```python
# 设置成本约束
plan = await orchestrator.plan(
    intent="research customer",
    context={"customer": "Acme"},
    constraints={
        "max_cost": 0.10,  # 最多$0.10
        "max_latency": 5.0
    }
)

# 使用成本优先路由
result = await mesh.call_capability(
    capability="market_research",
    strategy=RoutingStrategy.LEAST_COST
)
```

---

## 📚 更多资源

- **完整文档**: [docs/MCP_2026_ADVANCED_ARCHITECTURE.md](../docs/MCP_2026_ADVANCED_ARCHITECTURE.md)
- **实现总结**: [docs/MCP_2026_IMPLEMENTATION_SUMMARY.md](../docs/MCP_2026_IMPLEMENTATION_SUMMARY.md)
- **API参考**: [docs/MCP_A2A_INTEGRATION_GUIDE.md](../docs/MCP_A2A_INTEGRATION_GUIDE.md)

---

## 🎓 学习路径

1. **Day 1**: 运行演示，理解核心概念
2. **Day 2**: 测试智能编排器
3. **Day 3**: 测试动态工具生成
4. **Day 4**: 测试服务网格
5. **Day 5**: 集成到实际项目

---

## 💬 获取帮助

遇到问题？

1. 查看文档
2. 运行测试: `pytest tests/test_mcp_*.py -v`
3. 查看示例: `examples/mcp_2026_advanced_demo.py`

---

**开始你的MCP 2026之旅！** 🚀
