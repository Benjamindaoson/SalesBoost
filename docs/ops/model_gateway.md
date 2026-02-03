# Model Gateway 配置指南

## 概述

Model Gateway 是 V3 架构的核心组件，负责统一管理多模型 Provider（OpenAI/Qwen/DeepSeek）的调用、路由、预算和降级。

## 配置项

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# OpenAI 配置
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，默认使用官方地址

# Qwen 配置（阿里云通义千问）
QWEN_API_KEY=sk-...  # DashScope API Key

# DeepSeek 配置
DEEPSEEK_API_KEY=sk-...
# DeepSeek 使用 OpenAI 兼容 API，base_url 自动设置为 https://api.deepseek.com

# V3 架构开关
AGENTIC_V3_ENABLED=true

# 预算配置（可选，有默认值）
MODEL_BUDGET_SESSION_TOKENS=10000
MODEL_BUDGET_TURN_TOKENS=2000
MODEL_BUDGET_EMERGENCY_RESERVE=0.1
```

### 默认配置

如果未配置 API Key，系统会使用 Mock Provider（仅用于测试）。

## Provider 配置

### OpenAI

1. 获取 API Key：https://platform.openai.com/api-keys
2. 设置环境变量：`OPENAI_API_KEY=sk-...`
3. 支持的模型：
   - `gpt-4`（默认，高质量）
   - `gpt-3.5-turbo`（快速，低成本）

### Qwen（通义千问）

1. 获取 API Key：https://dashscope.aliyun.com/
2. 设置环境变量：`QWEN_API_KEY=sk-...`
3. 安装依赖：`pip install dashscope`
4. 支持的模型：
   - `qwen-plus`（高质量）
   - `qwen-turbo`（快速）

### DeepSeek

1. 获取 API Key：https://platform.deepseek.com/
2. 设置环境变量：`DEEPSEEK_API_KEY=sk-...`
3. 安装依赖：`pip install openai`（使用 OpenAI SDK）
4. 支持的模型：
   - `deepseek-chat`（低成本，高质量）

## 路由策略

### 按 Agent Type

- **Session Director**: Qwen Turbo（快速决策）
- **Retriever**: DeepSeek（低成本 embedding）
- **NPC Generator**: Qwen Turbo（Fast Path）
- **Coach Generator**: OpenAI GPT-4（高质量建议）
- **Evaluator**: OpenAI GPT-4（一致性要求）
- **Adoption Tracker**: Qwen Turbo（轻量任务）

### 按 Turn Importance

- **重要性 > 0.8**: 升级到强模型（GPT-4）
- **重要性 < 0.5**: 使用便宜模型（Qwen Turbo）

### 按 Budget

- **预算充足**: 使用强模型
- **预算不足**: 自动降级到便宜模型

### 按 Latency Mode

- **Fast Path**: 优先快速模型（Qwen Turbo）
- **Slow Path**: 允许慢速但高质量模型（GPT-4）

## 预算管理

### 默认预算

- **每轮预算**: $0.05
  - Fast Path: $0.02
  - Slow Path: $0.03
- **每会话预算**: $1.00

### 预算扣减

每次模型调用会自动扣减对应成本：
- GPT-4: ~$0.05/轮
- GPT-3.5: ~$0.002/轮
- Qwen Plus: ~$0.003/轮
- Qwen Turbo: ~$0.001/轮
- DeepSeek: ~$0.0007/轮

### 预算不足处理

当预算不足时：
1. 自动降级到便宜模型
2. 如果仍不足，停止非必要调用
3. 记录警告日志

## 降级策略

### 超时降级

- Fast Path > 3s: 降级到最快模型
- Slow Path > 30s: 降级到便宜模型

### 错误降级

- Provider 错误: 自动切换 Provider
- Schema 校验失败: 修复重试 → 降级输出

### 预算降级

- 预算不足: 优先使用便宜模型
- 预算耗尽: 停止非必要调用

## 切换 Provider

### 方法 1: 环境变量

修改 `.env` 文件中的 API Key，重启服务。

### 方法 2: 代码配置

在 `app/services/model_gateway/router.py` 中修改 `_get_default_model()` 方法。

## 测试

### Mock Provider

如果未配置真实 API Key，系统会自动使用 Mock Provider（用于测试）。

### 测试路由

```python
from app.services.model_gateway import ModelGateway, RoutingContext, AgentType, LatencyMode

gateway = ModelGateway()
context = RoutingContext(
    agent_type=AgentType.NPC_GENERATOR,
    turn_importance=0.5,
    risk_level="low",
    budget_remaining=0.1,
    latency_mode=LatencyMode.FAST,
    turn_number=1,
    session_id="test-session",
)

decision = gateway.router.route(context)
print(f"Selected: {decision.provider}/{decision.model}")
```

## 监控

### 调用统计

```python
stats = gateway.get_stats()
print(stats["call_stats"])  # {provider/model: count}
```

### 预算追踪

```python
remaining = gateway.budget_manager.get_remaining_budget(session_id)
print(f"Remaining budget: ${remaining:.2f}")
```

## 故障排查

### Provider 初始化失败

1. 检查 API Key 是否正确
2. 检查网络连接
3. 检查依赖是否安装（`pip install openai dashscope`）

### 路由选择错误

1. 检查 `router.py` 中的默认模型配置
2. 检查模型配置是否在 `model_configs` 中

### 预算不足

1. 检查 `BudgetConfig` 设置
2. 检查会话预算是否已耗尽
3. 考虑增加预算或优化模型选择

## 最佳实践

1. **生产环境**: 配置所有 Provider，启用自动降级
2. **开发环境**: 使用 Mock Provider 或单一 Provider
3. **测试环境**: 使用 Mock Provider，避免真实 API 调用成本
4. **监控**: 定期检查调用统计和预算使用情况
5. **优化**: 根据实际使用情况调整路由策略和预算分配
