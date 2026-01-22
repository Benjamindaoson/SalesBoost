# V3 P0 集成最终总结

## ✅ 完成清单

### 1. V3 Agent Wrapper（5个）✅

| Agent | 文件 | 状态 | 说明 |
|-------|------|------|------|
| RetrieverV3 | `app/agents/v3/retriever_v3.py` | ✅ | 封装 RAG/GraphRAG，Fast Path 只允许 lightweight |
| NPCGeneratorV3 | `app/agents/v3/npc_generator_v3.py` | ✅ | 封装 NPC Agent，输出 NpcReply |
| CoachGeneratorV3 | `app/agents/v3/coach_generator_v3.py` | ✅ | 封装 Coach Agent，输出 CoachAdvice（含 guardrails） |
| EvaluatorV3 | `app/agents/v3/evaluator_v3.py` | ✅ | 封装 Evaluator Agent，固定低温/模型（HR-4） |
| AdoptionTrackerV3 | `app/agents/v3/adoption_tracker_v3.py` | ✅ | 封装 Adoption Tracker，输出 AdoptionLog |

### 2. WebSocket 主入口接入 V3 ✅

- **文件**: `app/api/endpoints/websocket.py`
- **实现**:
  - 根据 `AGENTIC_V3_ENABLED` 切换 V2/V3
  - V3 路径调用 `v3_orchestrator.process_turn()`
  - 保持 API 契约不变（前端兼容）

### 3. Router Rulebook 硬规则（HR-1~HR-4）✅

- **文件**: `app/services/model_gateway/router_rulebook.py`
- **实现**:
  - ✅ HR-1: 预算熔断（`budget_remaining < 0.01` => 禁 STRONG_* + 禁 GraphRAG）
  - ✅ HR-2: 快路径不可阻塞（Fast Path => 禁 STRONG_CHAT + 禁 GraphRAG）
  - ✅ HR-3: 低置信度禁止确定性强回答（`confidence < 0.6` => 添加确认点 + 禁 STRONG_CHAT）
  - ✅ HR-4: Evaluator 一致性（固定模型/低温，不允许随机切）
- **测试**: `tests/test_v3_integration.py::test_router_hard_rules`

### 4. 指标埋点 ✅

- **文件**: `app/services/v3_orchestrator.py`, `app/services/model_gateway/gateway.py`
- **指标**（日志级）:
  - ✅ `fast_path_ttfs_ms`: Fast Path TTFS
  - ✅ `slow_path_total_ms`: Slow Path 总耗时
  - ✅ `provider_hit`: Provider 命中（openai/qwen/deepseek）
  - ✅ `model_hit`: 模型命中
  - ✅ `downgrade_count`: 降级次数
  - ✅ `downgrade_reason`: 降级原因
  - ✅ `token_usage`: Token 使用量
  - ✅ `estimated_cost`: 估算成本

### 5. 最小集成测试 ✅

- **文件**: `tests/test_v3_integration.py`
- **测试用例**:
  - ✅ `test_fast_path_not_blocked`: Fast Path 不被 Slow Path 阻塞
  - ✅ `test_router_hard_rules`: Router 硬规则 HR-1~HR-4
  - ✅ `test_schema_validation`: Schema 校验失败处理
  - ✅ `test_budget_fuse`: 预算熔断测试

---

## 文件改动列表

### 新增文件（7个）

1. `app/agents/v3/retriever_v3.py` - Retriever V3 Wrapper（封装 RAG/GraphRAG）
2. `app/agents/v3/npc_generator_v3.py` - NPC Generator V3 Wrapper
3. `app/agents/v3/coach_generator_v3.py` - Coach Generator V3 Wrapper
4. `app/agents/v3/evaluator_v3.py` - Evaluator V3 Wrapper（固定模型/低温）
5. `app/agents/v3/adoption_tracker_v3.py` - Adoption Tracker V3 Wrapper
6. `app/services/model_gateway/router_rulebook.py` - Router Rulebook 硬规则实现
7. `tests/test_v3_integration.py` - 集成测试

### 修改文件（4个）

1. `app/services/v3_orchestrator.py`
   - 集成所有 V3 Agents（Retriever/NPC/Coach/Evaluator/AdoptionTracker）
   - 添加指标埋点（fast_path_ttfs_ms, slow_path_total_ms）
   - 完善 Fast/Slow Path 实现

2. `app/services/model_gateway/router.py`
   - 集成 RouterRulebook，自动应用硬规则 HR-1~HR-4

3. `app/services/model_gateway/gateway.py`
   - 添加指标埋点（provider_hit, model_hit, downgrade_count, token_usage, estimated_cost）
   - 记录降级原因

4. `app/api/endpoints/websocket.py`
   - 添加 V3 路径支持（根据 `AGENTIC_V3_ENABLED` 切换）
   - 支持 V3Orchestrator 类型

---

## 如何运行测试

### 1. 安装依赖

```bash
pip install pytest pytest-asyncio
```

### 2. 运行测试

```bash
# 运行所有 V3 集成测试
pytest tests/test_v3_integration.py -v

# 运行特定测试
pytest tests/test_v3_integration.py::test_fast_path_not_blocked -v
pytest tests/test_v3_integration.py::test_router_hard_rules -v
pytest tests/test_v3_integration.py::test_schema_validation -v
pytest tests/test_v3_integration.py::test_budget_fuse -v
```

### 3. 预期结果

```
tests/test_v3_integration.py::test_fast_path_not_blocked PASSED
tests/test_v3_integration.py::test_router_hard_rules PASSED
tests/test_v3_integration.py::test_schema_validation PASSED
tests/test_v3_integration.py::test_budget_fuse PASSED
```

### 4. Mock Provider 测试（无需真实 API Key）

```bash
# 使用 Mock Provider（默认，无需配置 API Key）
AGENTIC_V3_ENABLED=true pytest tests/test_v3_integration.py -v
```

---

## 如何手动验证

### 1. 启动服务

```bash
# 设置环境变量启用 V3
export AGENTIC_V3_ENABLED=true

# 或修改 .env 文件
# AGENTIC_V3_ENABLED=true

# 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 连接 WebSocket

使用 WebSocket 客户端连接：

```bash
# 方式1：使用 websocat（如果已安装）
websocat ws://localhost:8000/ws/train?course_id=xxx&scenario_id=xxx&persona_id=xxx&user_id=test-user

# 方式2：使用浏览器 DevTools Console
const ws = new WebSocket('ws://localhost:8000/ws/train?course_id=xxx&scenario_id=xxx&persona_id=xxx&user_id=test-user');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({type: "text", content: "这张卡有什么权益？"}));
```

### 3. 发送消息并观察日志

发送消息：
```json
{"type": "text", "content": "这张卡有什么权益？"}
```

观察日志输出（关键指标）：

```
# Fast Path TTFS
INFO: Fast Path completed: turn=1, ttfs=1234.5ms [METRIC: fast_path_ttfs_ms=1234.5]

# Provider/Model 命中
INFO: [METRIC: provider_hit=qwen, model_hit=qwen_turbo, tokens=150, cost=$0.0001, latency=1234ms]

# 降级（如果有）
WARNING: Primary provider failed: ..., trying fallback
INFO: [METRIC: downgrade_count=1, downgrade_reason=provider_error: ...]

# Slow Path（异步）
INFO: Slow Path completed: turn=1, latency=5678.9ms [METRIC: slow_path_total_ms=5678.9]

# 硬规则触发
WARNING: HR-1 Budget fuse triggered: budget=$0.0050
INFO: HR-2: Fast path, downgraded to fast model
```

### 4. 验证硬规则

#### HR-1: 预算熔断
1. 修改代码或配置，将预算设置为 < $0.01
2. 发送消息
3. 观察日志：`HR-1 Budget fuse triggered`
4. 验证：GraphRAG 被禁用，模型降级到便宜模型

#### HR-2: 快路径不可阻塞
1. 发送消息
2. 观察 Fast Path TTFS：应该 < 3s
3. 验证：使用快速模型（Qwen Turbo），不使用 GPT-4

#### HR-3: 低置信度
1. Mock 低置信度检索（修改 RetrieverV3 返回 confidence < 0.6）
2. 发送消息
3. 验证：Coach/NPC 输出包含确认点或假设条件

#### HR-4: Evaluator 一致性
1. 多次调用 Evaluator（需要多轮对话）
2. 观察日志：应该使用固定模型（GPT-4 或 Qwen Plus）
3. 验证：温度固定为 0.1

---

## 未完成项与阻塞原因

### 1. Slow Path 结果推送机制 ⚠️

**状态**: 部分完成
**阻塞原因**: 
- Slow Path 异步执行，结果需要通过回调或事件机制推送到前端
- 当前实现中，Slow Path 结果未自动推送到 WebSocket

**下一步**:
- 实现 Slow Path 结果回调机制
- 或使用 WebSocket 事件推送 Slow Path 结果（coach_advice, evaluation）

### 2. Schema 校验失败自动修复 ⚠️

**状态**: Schema 定义完成，自动修复逻辑未完全实现
**阻塞原因**:
- 需要实现修复重试逻辑（使用便宜模型尝试修复）
- 需要定义降级输出格式

**下一步**:
- 实现 Schema 修复服务（`app/services/schema_repair.py`）
- 添加降级输出生成逻辑

### 3. 完整端到端测试 ⚠️

**状态**: 最小测试集完成，完整 E2E 测试未实现
**阻塞原因**:
- 需要 Mock 所有 Agent 和数据库
- 需要验证完整 Turn Loop

**下一步**:
- 实现完整 E2E 测试（Mock 所有依赖）
- 验证 Fast Path + Slow Path 完整流程

### 4. Prometheus 指标集成 ⚠️

**状态**: 日志级完成，Prometheus 未实现
**阻塞原因**:
- Prometheus 集成需要额外配置和依赖
- 当前使用日志级指标，可后续升级

**下一步**:
- 添加 Prometheus metrics exporter
- 配置 Prometheus 采集

---

## 关键指标验证方法

### Fast Path TTFS

```python
# 从日志提取
# INFO: Fast Path completed: turn=1, ttfs=1234.5ms [METRIC: fast_path_ttfs_ms=1234.5]
# 验证：< 3000ms
```

### Slow Path 延迟

```python
# INFO: Slow Path completed: turn=1, latency=5678.9ms [METRIC: slow_path_total_ms=5678.9]
# 验证：5-30s 范围内
```

### 路由命中率

```python
# 从 orchestrator.metrics 获取
metrics = orchestrator.get_metrics()
provider_hits = metrics["provider_hits"]
# 验证：便宜模型占比 > 80%（成本优化）
```

### 降级次数

```python
# INFO: [METRIC: downgrade_count=1, downgrade_reason=...]
# 验证：< 10%（系统稳定性）
```

---

## 回滚方式

### 方法 1: 配置开关（推荐）

```bash
# 回滚到 V2
export AGENTIC_V3_ENABLED=false
# 或修改 .env 文件
# AGENTIC_V3_ENABLED=false

# 重启服务
uvicorn app.main:app --reload
```

### 方法 2: Git 回滚

```bash
# 回滚到重构前的 commit
git checkout <previous-commit-hash>
```

---

## 总结

V3 P0 集成已完成核心功能，系统可以运行：

✅ **5 个 V3 Agent Wrapper**：全部完成，封装现有实现
✅ **WebSocket 集成**：支持 V2/V3 切换，API 契约不变
✅ **Router Rulebook**：4 条硬规则全部实现并测试
✅ **指标埋点**：日志级完成，可观测
✅ **集成测试**：最小测试集完成

**关键成果**：
1. ✅ 双流架构可运行（Fast Path <3s，Slow Path 异步）
2. ✅ 硬规则可执行（HR-1~HR-4）
3. ✅ 指标可观测（日志级）
4. ✅ 可回滚（配置开关）

**下一步**：
1. 完善 Slow Path 结果推送机制
2. 实现 Schema 校验失败自动修复
3. 完整端到端测试
4. Prometheus 指标集成（可选）

**验证方式**：
- 运行测试：`pytest tests/test_v3_integration.py -v`
- 手动验证：启动服务，连接 WebSocket，观察日志指标

