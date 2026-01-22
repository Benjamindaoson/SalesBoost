# SalesBoost 模拟平台使用示例

## 🚀 快速开始

### 1. 验证安装

```bash
# 运行快速测试
cd D:\SalesBoost
python app/sales_simulation/test_quick.py
```

**预期输出**：
```
==================================================
SalesBoost 模拟平台快速测试
==================================================
INFO: Testing ScenarioLoader...
INFO: Found 3 scenarios: ['scenario_001_cold_call', 'scenario_002_objection_handling', 'scenario_003_closing']
INFO: Loaded scenario: SaaS产品冷呼场景
...
✅ 所有测试通过！
==================================================
```

---

## 📋 CLI 使用示例

### 列出所有场景

```bash
python -m app.sales_simulation.cli list
```

**输出**：
```
可用场景:
  - scenario_001_cold_call
  - scenario_002_objection_handling
  - scenario_003_closing
```

### 运行单智能体模拟

```bash
python -m app.sales_simulation.cli run \
  --scenario scenario_001_cold_call \
  --agent-type single \
  --num-runs 5 \
  --seed 42
```

**输出**：
```
2026-01-19 10:30:00 - INFO - Starting simulation: scenario=scenario_001_cold_call, agent_type=single, num_runs=5
2026-01-19 10:30:01 - INFO - Loaded scenario: SaaS产品冷呼场景
2026-01-19 10:30:01 - INFO - Running trajectory 1/5
2026-01-19 10:30:15 - INFO - Trajectory 1 completed: steps=12, score=0.82, goal_achieved=True
...
2026-01-19 10:32:00 - INFO - Calculating metrics...
2026-01-19 10:32:01 - INFO - Generating report...
2026-01-19 10:32:02 - INFO - Reports saved: report_cli_run_scenario_001_cold_call.json, report_cli_run_scenario_001_cold_call.md

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

### 运行多智能体模拟

```bash
python -m app.sales_simulation.cli run \
  --scenario scenario_002_objection_handling \
  --agent-type multi \
  --num-runs 10 \
  --seed 100
```

---

## 🌐 API 使用示例

### 启动服务

```bash
# 1. 应用数据库迁移
alembic upgrade head

# 2. 启动 FastAPI 服务
python -m app.main
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 列出场景

```bash
curl http://localhost:8000/api/v1/sales-sim/run/scenarios
```

**响应**：
```json
{
  "scenarios": [
    "scenario_001_cold_call",
    "scenario_002_objection_handling",
    "scenario_003_closing"
  ],
  "count": 3
}
```

### 启动模拟运行

```bash
curl -X POST http://localhost:8000/api/v1/sales-sim/run/ \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "scenario_001_cold_call",
    "agent_type": "single",
    "num_trajectories": 5,
    "seed": 42
  }'
```

**响应**：
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "message": "Successfully completed 5 trajectories",
  "num_trajectories": 5
}
```

### 查询评估结果

```bash
curl http://localhost:8000/api/v1/sales-sim/eval/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**响应**：
```json
{
  "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "summary": {
    "num_trajectories": 5,
    "success_rate": 0.8,
    "avg_score": 0.82,
    "overall_quality": 0.85
  },
  "recommendation": "Agent 表现优秀且稳定，推荐用于生产环境"
}
```

### 列出数据集

```bash
curl http://localhost:8000/api/v1/sales-sim/datasets/
```

**响应**：
```json
{
  "datasets": [
    {"id": "preference_pairs_001", "type": "dpo", "size": 150},
    {"id": "sft_samples_001", "type": "sft", "size": 500}
  ],
  "count": 2
}
```

---

## 🐍 Python 代码示例

### 基础使用

```python
import asyncio
from app.sales_simulation.scenarios.loader import ScenarioLoader
from app.sales_simulation.runners.single_agent_runner import SingleAgentRunner
from app.sales_simulation.evaluation.metrics_calculator import MetricsCalculator

async def main():
    # 1. 加载场景
    loader = ScenarioLoader()
    scenario = loader.load_scenario("scenario_001_cold_call")
    print(f"场景: {scenario.name}")
    print(f"客户: {scenario.customer_profile.name}")
    print(f"目标: {scenario.sales_goal.goal_type}")
    
    # 2. 创建运行器
    runner = SingleAgentRunner(scenario)
    
    # 3. 运行多条轨迹
    trajectories = []
    for i in range(5):
        print(f"\n运行轨迹 {i+1}/5...")
        trajectory = await runner.run("demo_run", i, seed=42+i)
        trajectories.append(trajectory)
        
        print(f"  步数: {trajectory.total_steps}")
        print(f"  得分: {trajectory.final_score:.2f}")
        print(f"  目标达成: {trajectory.goal_achieved}")
    
    # 4. 计算聚合指标
    metrics = MetricsCalculator.calculate_aggregated_metrics("demo_run", trajectories)
    
    print(f"\n{'='*50}")
    print(f"成功率: {metrics.success_rate:.1%}")
    print(f"平均得分: {metrics.avg_score:.2f}")
    print(f"稳定性: {metrics.consistency_metrics.stability_score:.2f}")
    print(f"推荐: {metrics.recommendation}")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 生成训练数据

```python
import asyncio
from app.sales_simulation.scenarios.loader import ScenarioLoader
from app.sales_simulation.runners.single_agent_runner import SingleAgentRunner
from app.sales_simulation.datasets.preference_generator import PreferenceGenerator
from app.sales_simulation.datasets.sft_generator import SFTGenerator
from app.sales_simulation.datasets.exporter import DatasetExporter

async def generate_training_data():
    # 1. 运行模拟
    loader = ScenarioLoader()
    scenario = loader.load_scenario("scenario_001_cold_call")
    runner = SingleAgentRunner(scenario)
    
    trajectories = []
    for i in range(10):
        trajectory = await runner.run("training_run", i, seed=100+i)
        trajectories.append(trajectory)
    
    # 2. 生成 DPO 偏好对
    print("生成 DPO 偏好对...")
    preference_pairs = PreferenceGenerator.generate_preference_pairs(
        trajectories=trajectories,
        run_id="training_run",
        scenario_id=scenario.id,
        min_score_delta=0.1
    )
    print(f"生成了 {len(preference_pairs)} 个偏好对")
    
    # 导出
    DatasetExporter.export_preference_pairs(
        pairs=preference_pairs,
        output_path="preference_pairs.jsonl"
    )
    
    # 3. 生成 SFT 样本
    print("生成 SFT 样本...")
    sft_samples = SFTGenerator.generate_sft_samples(
        trajectories=trajectories,
        quality_threshold=0.7
    )
    print(f"生成了 {len(sft_samples)} 个 SFT 样本")
    
    # 导出
    DatasetExporter.export_sft_samples(
        samples=sft_samples,
        output_path="sft_samples.jsonl"
    )
    
    print("\n训练数据生成完成！")
    print(f"  - preference_pairs.jsonl ({len(preference_pairs)} 条)")
    print(f"  - sft_samples.jsonl ({len(sft_samples)} 条)")

if __name__ == "__main__":
    asyncio.run(generate_training_data())
```

### 自定义场景

```python
from app.sales_simulation.schemas.scenario import (
    SimulationScenario,
    CustomerProfile,
    SalesGoal,
    ScenarioConfig,
    CustomerType,
    DifficultyLevel,
)

# 创建自定义场景
custom_scenario = SimulationScenario(
    id="custom_001",
    name="高端客户咨询场景",
    description="向高净值客户推荐金融产品",
    difficulty=DifficultyLevel.EXPERT,
    customer_profile=CustomerProfile(
        name="张总",
        company="某投资公司",
        role="CEO",
        customer_type=CustomerType.WARM_LEAD,
        personality_traits=["果断", "专业", "时间宝贵"],
        pain_points=["资产配置", "风险管理", "税务筹划"],
        objections=["收益率", "风险等级", "流动性"],
        decision_style="emotional",
        budget_sensitivity=0.2,
        urgency_level=0.8,
        initial_mood=0.6,
        initial_interest=0.7,
    ),
    sales_goal=SalesGoal(
        goal_type="purchase",
        target_value=1000000,
        success_criteria=[
            "客户理解产品价值",
            "客户同意投资",
            "确认投资金额和时间"
        ]
    ),
    config=ScenarioConfig(
        max_turns=15,
        timeout_seconds=900,
        enable_interruption=True,
        enable_emotion_drift=True,
        goal_weight=0.5,
        process_weight=0.3,
        compliance_weight=0.2,
    ),
    background_context="客户是成功企业家，寻求高端金融服务",
    product_info={
        "name": "私人银行服务",
        "category": "金融",
        "min_investment": 1000000
    },
    tags=["high_net_worth", "financial", "consulting"],
)

# 保存为 JSON
import json
with open("custom_scenario.json", "w", encoding="utf-8") as f:
    json.dump(custom_scenario.model_dump(), f, ensure_ascii=False, indent=2)

print("自定义场景已保存: custom_scenario.json")
```

---

## 📊 报告示例

### JSON 报告

```json
{
  "run_id": "cli_run_scenario_001_cold_call",
  "generated_at": "2026-01-19T10:32:00.123456",
  "summary": {
    "num_trajectories": 5,
    "success_rate": 0.8,
    "avg_score": 0.82,
    "overall_quality": 0.85
  },
  "metrics": {
    "run_id": "cli_run_scenario_001_cold_call",
    "num_trajectories": 5,
    "success_rate": 0.8,
    "completion_rate": 1.0,
    "avg_score": 0.82,
    "avg_steps": 13.5,
    "avg_duration": 267.3,
    "score_distribution": {
      "0.7-0.8": 1,
      "0.8-0.9": 3,
      "0.9-1.0": 1
    },
    "consistency_metrics": {
      "num_trajectories": 5,
      "score_std_dev": 0.08,
      "stability_score": 0.88
    },
    "overall_quality": 0.85,
    "recommendation": "Agent 表现优秀且稳定，推荐用于生产环境"
  },
  "recommendation": "Agent 表现优秀且稳定，推荐用于生产环境",
  "trajectories_summary": [
    {
      "id": "traj_001",
      "goal_achieved": true,
      "final_score": 0.85,
      "total_steps": 12
    },
    ...
  ]
}
```

### Markdown 报告

```markdown
# 销售模拟评估报告

## 基本信息
- **运行 ID**: cli_run_scenario_001_cold_call
- **生成时间**: 2026-01-19T10:32:00
- **轨迹数量**: 5

## 核心指标
- **成功率**: 80.0%
- **平均得分**: 0.82
- **平均步数**: 13.5
- **整体质量**: 0.85

## 一致性分析
- **得分标准差**: 0.080
- **稳定性评分**: 0.88

## 推荐建议
Agent 表现优秀且稳定，推荐用于生产环境
```

---

## 🎯 高级用法

### 批量运行多个场景

```python
import asyncio
from app.sales_simulation.scenarios.loader import ScenarioLoader
from app.sales_simulation.runners.single_agent_runner import SingleAgentRunner
from app.sales_simulation.evaluation.metrics_calculator import MetricsCalculator

async def batch_run():
    loader = ScenarioLoader()
    all_scenarios = loader.load_all_scenarios()
    
    results = {}
    
    for scenario in all_scenarios:
        print(f"\n运行场景: {scenario.name}")
        runner = SingleAgentRunner(scenario)
        
        trajectories = []
        for i in range(5):
            trajectory = await runner.run(f"batch_{scenario.id}", i, seed=42+i)
            trajectories.append(trajectory)
        
        metrics = MetricsCalculator.calculate_aggregated_metrics(
            f"batch_{scenario.id}", trajectories
        )
        
        results[scenario.id] = {
            "name": scenario.name,
            "success_rate": metrics.success_rate,
            "avg_score": metrics.avg_score,
            "recommendation": metrics.recommendation,
        }
    
    # 输出汇总
    print("\n" + "="*70)
    print("批量运行汇总")
    print("="*70)
    for scenario_id, result in results.items():
        print(f"\n场景: {result['name']}")
        print(f"  成功率: {result['success_rate']:.1%}")
        print(f"  平均得分: {result['avg_score']:.2f}")
        print(f"  推荐: {result['recommendation']}")

if __name__ == "__main__":
    asyncio.run(batch_run())
```

---

## 🔧 故障排查

### 问题 1: 场景文件未找到

**错误**:
```
FileNotFoundError: Scenario file not found: ...
```

**解决**:
```bash
# 检查场景目录
ls app/sales_simulation/scenarios/data/

# 确认场景 ID 正确
python -m app.sales_simulation.cli list
```

### 问题 2: LLM 调用失败

**错误**:
```
ConfigurationError: OPENAI_API_KEY is required
```

**解决**:
```bash
# 设置环境变量
export OPENAI_API_KEY=your_key_here

# 或在 .env 文件中配置
echo "OPENAI_API_KEY=your_key_here" >> .env
```

**注意**: 系统会自动降级到规则模式，不影响基本功能。

### 问题 3: 数据库迁移

**错误**:
```
sqlalchemy.exc.OperationalError: no such table: simulation_runs
```

**解决**:
```bash
# 应用迁移
alembic upgrade head

# 检查迁移状态
alembic current
```

---

## 📚 更多资源

- **完整文档**: `app/sales_simulation/README.md`
- **实施报告**: `SALES_SIMULATION_IMPLEMENTATION.md`
- **API 文档**: http://localhost:8000/docs
- **快速测试**: `python app/sales_simulation/test_quick.py`

---

**最后更新**: 2026-01-19





