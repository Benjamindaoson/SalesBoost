# V3 P0 集成完成报告

## 概述

已完成 V3 架构的 P0 集成，使 V3 真正跑通生产 turn loop，并可验证 TTFS、路由与降级行为。

## 文件改动列表

### 1. Agent V3 Wrapper（5个）

#### `app/agents/v3/retriever_v3.py` (新建)
- **摘要**: 封装现有 RAG/GraphRAG，输出 EvidencePack
- **关键逻辑**:
  - Fast Path: 只允许 lightweight retrieval（基础向量检索）
  - GraphRAG: 只能 Slow Path 且 hard budget >= 0.01
  - HR-1/HR-2: 预算熔断和快路径不可阻塞规则

#### `app/agents/v3/npc_generator_v3.py` (新建)
- **摘要**: 封装现有 NPC agent，输出 NpcReply
- **关键逻辑**:
  - 调用现有 NPCAgent.generate_response()
  - HR-3: 低置信度时在 prompt 中强调不确定性

#### `app/agents/v3/coach_generator_v3.py` (新建)
- **摘要**: 封装现有 Coach agent，输出 CoachAdvice（结构化，含 guardrails）
- **关键逻辑**:
  - 转换 RAGOutput/ComplianceOutput 到 V3 Schema
  - HR-3: 低置信度时添加不确定性提示和 guardrails

#### `app/agents/v3/evaluator_v3.py` (新建)
- **摘要**: 封装现有 Evaluator agent，输出 Evaluation
- **关键逻辑**:
  - HR-4: 固定低温（temperature=0.1）
  - 固定模型选择（首次调用时确定，后续不变）

#### `app/agents/v3/adoption_tracker_v3.py` (新建)
- **摘要**: 封装现有 adoption tracker，输出 AdoptionLog
- **关键逻辑**:
  - 追踪建议→采纳→skill_delta

### 2. Router 硬规则实现

#### `app/services/model_gateway/router_rulebook.py` (新建)
- **摘要**: Router Rulebook 硬规则实现
- **实现规则**:
  - HR-1: 预算熔断（budget_remaining < 0.01 => 禁 STRONG_* + 禁 GraphRAG + 强制 CHEAP）
  - HR-2: 快路径不可阻塞（npc + latency_mode=fast => 禁 STRONG_CHAT + 禁 GraphRAG）
  - HR-3: 低置信度禁止确定性强回答（retrieval_confidence < 0.6 => 禁 STRONG_CHAT）
  - HR-4: Evaluator 一致性（固定模型/低温）

#### `app/services/model_gateway/router.py` (修改)
- **摘要**: 在 route() 方法中直接应用硬规则 HR-1~HR-4
- **改动**: 在路由决策后应用硬规则，更新 decision.reason

### 3. V3 Orchestrator 集成

#### `app/services/v3_orchestrator.py` (修改)
- **摘要**: 集成 5 个 Agent V3 wrapper，实现双流架构
- **关键改动**:
  - `_retrieve_lightweight()`: Fast Path 轻量检索
  - `_generate_npc_reply()`: Fast Path NPC 生成
  - `_generate_coach_advice()`: Slow Path 教练建议
  - `_evaluate_turn()`: Slow Path 评估
  - `_track_adoption()`: Slow Path 采纳追踪
  - `_execute_slow_path_async()`: 异步执行 Slow Path 并推送结果

### 4. WebSocket 集成

#### `app/api/endpoints/websocket.py` (修改)
- **摘要**: WebSocket 主入口接入 V3
- **关键改动**:
  - 根据 `AGENTIC_V3_ENABLED` 切换 V2/V3
  - V3 路径：调用 `v3_orchestrator.process_turn()`
  - 立即发送 Fast Path 结果（NPC 回复 + TTFS 指标）
  - Slow Path 结果异步推送（通过 `turn_analysis` 消息）

### 5. 指标埋点

#### `app/services/model_gateway/gateway.py` (修改)
- **摘要**: 添加指标埋点（日志级）
- **埋点指标**:
  - `provider_hit`, `model_hit`: 路由命中
  - `tokens`, `cost`, `latency`: 调用统计
  - `downgrade_count`, `downgrade_reason`: 降级统计

#### `app/services/v3_orchestrator.py` (修改)
- **摘要**: 添加 Fast/Slow Path 指标埋点
- **埋点指标**:
  - `fast_path_ttfs_ms`: Fast Path TTFS
  - `slow_path_total_ms`: Slow Path 总延迟
  - `provider_hits`, `model_hits`: 路由统计

### 6. 测试文件

#### `tests/test_v3_integration.py` (新建)
- **摘要**: V3 集成测试
- **测试用例**:
  - `test_fast_path_not_blocked`: Fast Path 不被 Slow Path 阻塞
  - `test_router_hard_rules`: Router 硬规则 HR-1~HR-4
  - `test_schema_validation`: Schema 校验失败触发修复重试
  - `test_budget_manager`: 预算管理器测试

## 如何运行测试

### 1. 运行集成测试

```bash
# 运行所有 V3 集成测试
pytest tests/test_v3_integration.py -v

# 运行特定测试
pytest tests/test_v3_integration.py::test_fast_path_not_blocked -v
pytest tests/test_v3_integration.py::test_router_hard_rules -v
```

### 2. 预期结果

- `test_fast_path_not_blocked`: Fast Path < 3s，即使 Slow Path mock sleep 2s
- `test_router_hard_rules`: HR-1~HR-4 规则正确应用
- `test_schema_validation`: Schema 校验通过
- `test_budget_manager`: 预算扣减正确

## 如何手动验证

### 1. 启动服务

```bash
# 设置环境变量启用 V3
export AGENTIC_V3_ENABLED=true

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 开启 V3 开关

在 `.env` 或环境变量中设置：
```
AGENTIC_V3_ENABLED=true
```

### 3. 一次对话观察日志

#### 启动 WebSocket 连接

```bash
# 使用 WebSocket 客户端连接
ws://localhost:8000/ws/training?session_id=test-session&user_id=test-user&course_id=test-course&scenario_id=test-scenario&persona_id=test-persona
```

#### 发送消息

```json
{
  "type": "message",
  "content": "你好，我想了解一下信用卡权益"
}
```

#### 观察日志输出

**Fast Path 日志**:
```
Fast Path completed: turn=1, ttfs=1234ms [METRIC: fast_path_ttfs_ms=1234]
```

**Router 日志**:
```
Routing decision: qwen/qwen-turbo for NPC_GENERATOR (Agent=NPC_GENERATOR, Importance=0.50, Budget=$1.00, Latency=fast, HR-2:FastPath)
```

**Slow Path 日志**:
```
Slow Path completed: turn=1, latency=5678ms [METRIC: slow_path_total_ms=5678]
```

**指标埋点日志**:
```
[METRIC: provider_hit=qwen, model_hit=qwen-turbo, tokens=150, cost=$0.001, latency=1234ms]
```

### 4. 验证硬规则

#### HR-1: 预算熔断

设置低预算：
```python
budget_manager.set_budget("test-session", 0.005)  # < 0.01
```

观察日志应显示：
```
HR-1: Budget critical ($0.0050), downgraded to mock
```

#### HR-2: 快路径不可阻塞

Fast Path 不应使用 GPT-4，日志应显示：
```
HR-2: Fast path, downgraded from GPT-4 to qwen-turbo
```

#### HR-3: 低置信度禁止确定性强回答

设置低检索置信度：
```python
retrieval_confidence = 0.5  # < 0.6
```

Coach/NPC 输出应包含不确定性提示。

#### HR-4: Evaluator 一致性

多次调用 Evaluator，观察模型选择应保持一致：
```
HR-4: Evaluator using fixed model: qwen-plus
```

## 关键接口请求/响应示例

### 1. WebSocket 消息（Fast Path 响应）

**请求**:
```json
{
  "type": "message",
  "content": "你好"
}
```

**响应**:
```json
{
  "type": "turn_result_partial",
  "turn": 1,
  "user_message": "你好",
  "npc_response": "您好，我是XX银行的客户经理，很高兴为您服务。",
  "npc_mood": 0.6,
  "processing_time_ms": 1234,
  "stage": "OPENING",
  "ttfs_ms": 1234,
  "metrics": {
    "fast_path_ttfs_ms": 1234,
    "provider_hits": {"qwen": 2}
  }
}
```

### 2. WebSocket 消息（Slow Path 响应）

**响应**:
```json
{
  "type": "turn_analysis",
  "turn": 1,
  "coach_advice": {
    "why": "客户表达了初步兴趣",
    "action": "可以介绍核心权益",
    "suggested_reply": "我们这张卡的核心权益包括...",
    "alternatives": ["备选话术1", "备选话术2"],
    "guardrails": [],
    "priority": "high",
    "confidence": 0.8
  },
  "evaluation": {
    "overall_score": 0.75,
    "goal_advanced": true,
    "error_tags": []
  },
  "slow_path_latency_ms": 5678
}
```

## 未完成项与阻塞原因

### 1. Slow Path 结果推送机制（部分完成）

**状态**: 已实现异步推送，但需要完善错误处理
**阻塞原因**: WebSocket manager 全局访问方式不够优雅
**下一步**: 重构为依赖注入或事件机制

### 2. Schema 校验失败修复重试（部分完成）

**状态**: Schema 定义完成，但修复重试逻辑未完全实现
**阻塞原因**: 需要在 Agent wrapper 中添加重试逻辑
**下一步**: 在 `CoachGeneratorV3` 和 `EvaluatorV3` 中添加 Schema 校验失败时的修复重试

### 3. Prometheus 指标导出（未开始）

**状态**: 目前只有日志级指标
**阻塞原因**: 需要集成 Prometheus 客户端
**下一步**: 添加 Prometheus metrics exporter

### 4. GraphRAG 集成测试（未开始）

**状态**: RetrieverV3 支持 GraphRAG，但未测试
**阻塞原因**: 需要 GraphRAG 服务可用
**下一步**: 添加 GraphRAG mock 或集成测试

## 总结

V3 P0 集成已完成核心功能：
- ✅ 5 个 Agent V3 wrapper 实现
- ✅ Router 硬规则 HR-1~HR-4 实现和测试
- ✅ WebSocket 主入口接入 V3
- ✅ 指标埋点（日志级）
- ✅ 最小集成测试

V3 架构已可跑通生产 turn loop，并可验证 TTFS、路由与降级行为。
