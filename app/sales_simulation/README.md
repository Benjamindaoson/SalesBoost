# SalesBoost 多智能体销售任务模拟平台

## 📖 概述

这是 SalesBoost 的**子系统级能力模块**，提供完整的销售任务模拟环境，用于：

- 🔬 **可复现模拟**：基于种子的确定性模拟，支持轨迹复现
- 🤖 **多智能体支持**：单智能体 / 多智能体协作模式
- 📊 **长周期评估**：目标达成、过程质量、一致性、漂移检测
- 🎯 **训练数据生成**：自动生成 SFT / DPO / GRPO 训练数据

## 🏗️ 架构设计

```
sales_simulation/
├── schemas/          # Pydantic v2 Schema 定义
├── scenarios/        # 场景 DSL（JSON/YAML）
├── environment/      # 模拟环境（Gym-like 接口）
├── agents/           # Planner / Dialogue / Critic Agent
├── evaluation/       # 指标计算与报告生成
├── datasets/         # 偏好数据生成器
├── models/           # 数据库模型
├── runners/          # 单/多智能体运行器
├── api/              # FastAPI 路由
└── cli.py            # 命令行接口
```

## 🚀 快速开始

### 1. CLI 方式运行

```bash
# 列出所有场景
python -m app.sales_simulation.cli list

# 运行单智能体模拟
python -m app.sales_simulation.cli run \
  --scenario scenario_001 \
  --agent-type single \
  --num-runs 5 \
  --seed 42

# 运行多智能体模拟
python -m app.sales_simulation.cli run \
  --scenario scenario_002 \
  --agent-type multi \
  --num-runs 10
```

### 2. API 方式运行

启动 FastAPI 服务后：

```bash
# 列出所有场景
curl http://localhost:8000/api/v1/sales-sim/run/scenarios

# 启动模拟运行
curl -X POST http://localhost:8000/api/v1/sales-sim/run/ \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "scenario_001",
    "agent_type": "single",
    "num_trajectories": 5,
    "seed": 42
  }'

# 查询评估结果
curl http://localhost:8000/api/v1/sales-sim/eval/{run_id}

# 列出数据集
curl http://localhost:8000/api/v1/sales-sim/datasets/
```

### 3. Python 代码调用

```python
import asyncio
from app.sales_simulation.scenarios.loader import ScenarioLoader
from app.sales_simulation.runners.single_agent_runner import SingleAgentRunner
from app.sales_simulation.evaluation.metrics_calculator import MetricsCalculator

async def main():
    # 加载场景
    loader = ScenarioLoader()
    scenario = loader.load_scenario("scenario_001")
    
    # 创建运行器
    runner = SingleAgentRunner(scenario)
    
    # 运行轨迹
    trajectories = []
    for i in range(5):
        trajectory = await runner.run("test_run", i, seed=42+i)
        trajectories.append(trajectory)
    
    # 计算指标
    metrics = MetricsCalculator.calculate_aggregated_metrics("test_run", trajectories)
    
    print(f"成功率: {metrics.success_rate:.1%}")
    print(f"平均得分: {metrics.avg_score:.2f}")
    print(f"推荐: {metrics.recommendation}")

asyncio.run(main())
```

## 📋 场景定义

场景使用 JSON 格式定义，包含以下核心组件：

```json
{
  "id": "scenario_001",
  "name": "SaaS产品冷呼场景",
  "difficulty": "medium",
  "customer_profile": {
    "name": "李明",
    "role": "技术总监",
    "customer_type": "cold_lead",
    "personality_traits": ["理性", "谨慎"],
    "pain_points": ["团队协作效率低"],
    "initial_mood": 0.4,
    "initial_interest": 0.3
  },
  "sales_goal": {
    "goal_type": "demo",
    "success_criteria": ["客户同意参加产品演示"]
  }
}
```

## 📊 评估指标

### 单轨迹指标
- **目标达成率**：goal_completion_rate
- **过程效率**：process_efficiency
- **对话质量**：dialogue_quality
- **合规率**：compliance_rate
- **客户满意度**：customer_satisfaction

### 多轨迹指标
- **成功率**：success_rate
- **一致性评分**：consistency_score
- **稳定性评分**：stability_score
- **得分标准差**：score_std_dev

### 报告输出
- **JSON 报告**：`report_{run_id}.json`
- **Markdown 报告**：`report_{run_id}.md`

## 🎯 训练数据生成

### SFT 样本生成

```python
from app.sales_simulation.datasets.sft_generator import SFTGenerator
from app.sales_simulation.datasets.exporter import DatasetExporter

# 生成 SFT 样本
samples = SFTGenerator.generate_sft_samples(
    trajectories=trajectories,
    quality_threshold=0.7
)

# 导出为 JSONL
DatasetExporter.export_sft_samples(
    samples=samples,
    output_path="sft_samples.jsonl"
)
```

### DPO 偏好对生成

```python
from app.sales_simulation.datasets.preference_generator import PreferenceGenerator

# 生成偏好对
pairs = PreferenceGenerator.generate_preference_pairs(
    trajectories=trajectories,
    run_id="run_001",
    scenario_id="scenario_001",
    min_score_delta=0.1
)

# 导出
DatasetExporter.export_preference_pairs(
    pairs=pairs,
    output_path="preference_pairs.jsonl"
)
```

## 🔧 配置说明

### 环境配置

场景配置文件中的 `config` 字段：

```json
{
  "max_turns": 20,
  "timeout_seconds": 600,
  "enable_interruption": true,
  "enable_emotion_drift": true,
  "goal_weight": 0.4,
  "process_weight": 0.3,
  "compliance_weight": 0.3
}
```

### Agent 配置

```python
{
  "type": "single",  # single / multi
  "model": "gpt-4",
  "temperature": 0.2,
  "max_tokens": 2000
}
```

## 📈 输出示例

### 控制台输出

```
==================================================
模拟运行完成
==================================================
场景: SaaS产品冷呼场景
轨迹数量: 5
成功率: 80.0%
平均得分: 0.82
整体质量: 0.85
推荐建议: Agent 表现优秀且稳定，推荐用于生产环境
==================================================
```

### JSON 报告

```json
{
  "run_id": "cli_run_scenario_001",
  "generated_at": "2026-01-19T10:30:00",
  "summary": {
    "num_trajectories": 5,
    "success_rate": 0.8,
    "avg_score": 0.82,
    "overall_quality": 0.85
  },
  "recommendation": "Agent 表现优秀且稳定，推荐用于生产环境"
}
```

## 🛠️ 扩展开发

### 添加新场景

1. 在 `scenarios/data/` 下创建 JSON 文件
2. 遵循 `SimulationScenario` Schema
3. 使用 `ScenarioLoader` 加载

### 自定义 Agent

继承 `BaseAgent` 并实现：

```python
from app.agents.roles.base import BaseAgent

class CustomAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "你的提示词"
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return YourOutputSchema
```

### 自定义评估指标

扩展 `MetricsCalculator`：

```python
class CustomMetricsCalculator(MetricsCalculator):
    @staticmethod
    def calculate_custom_metric(trajectory):
        # 自定义计算逻辑
        pass
```

## 📚 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔍 故障排查

### 常见问题

1. **场景文件未找到**
   - 检查 `scenarios/data/` 目录
   - 确认场景 ID 正确

2. **LLM 调用失败**
   - 检查 `OPENAI_API_KEY` 配置
   - 查看日志中的错误信息
   - 系统会自动降级到规则模式

3. **数据库迁移**
   ```bash
   alembic upgrade head
   ```

## 📄 许可证

本模块遵循 SalesBoost 项目许可证（MIT）。





