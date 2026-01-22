# V3 架构重构完成报告

## ✅ 完成清单

### 0. 第一性原理 ✅
- [x] 创建系统设计文档 `docs/system_design/agentic_architecture_v3.md`
- [x] 定义系统目标函数（最小化延迟/成本/不可控性，最大化可度量性/可演进性/可扩展性）
- [x] 定义系统不变量（控制层/执行层/裁判层分离、快慢分离、可审计输出、硬预算）

### 1. 6-Agent 架构 ✅
- [x] Session Director（控制器）- `app/agents/v3/session_director_v3.py`
- [x] Retriever（证据构造器）- Schema 定义完成，实现待集成
- [x] NPC Generator（客户模拟器）- Schema 定义完成，实现待集成
- [x] Coach Generator（教练）- Schema 定义完成，实现待集成
- [x] Evaluator（裁判）- Schema 定义完成，实现待集成
- [x] Adoption & Attribution Tracker（采纳归因器）- Schema 定义完成，实现待集成

### 2. Model Gateway + Router ✅
- [x] Provider 抽象接口 - `app/services/model_gateway/providers/base.py`
- [x] Mock Provider（测试用）- `app/services/model_gateway/providers/mock.py`
- [x] OpenAI Provider - `app/services/model_gateway/providers/openai_provider.py`
- [x] Qwen Provider - `app/services/model_gateway/providers/qwen_provider.py`
- [x] DeepSeek Provider - `app/services/model_gateway/providers/deepseek_provider.py`
- [x] Model Router - `app/services/model_gateway/router.py`
- [x] Budget Manager - `app/services/model_gateway/budget.py`
- [x] Model Gateway - `app/services/model_gateway/gateway.py`

### 3. 双流编排 ✅
- [x] V3 Orchestrator - `app/services/v3_orchestrator.py`
- [x] Fast Path 实现（<3s TTFS）
- [x] Slow Path 实现（异步，5-30s）
- [x] 双流分离逻辑

### 4. 结构化 Schema ✅
- [x] V3 Agent Outputs Schema - `app/schemas/v3_agent_outputs.py`
  - TurnPlan
  - EvidencePack
  - NpcReply
  - CoachAdvice
  - Evaluation
  - AdoptionLog

### 5. 文档 ✅
- [x] 系统设计文档 - `docs/system_design/agentic_architecture_v3.md`
- [x] Model Gateway 配置指南 - `docs/ops/model_gateway.md`

### 6. 待完成（需要集成现有 Agent）
- [ ] 集成现有 RAG Agent 到 Retriever V3
- [ ] 集成现有 NPC Agent 到 NPC Generator V3
- [ ] 集成现有 Coach Agent 到 Coach Generator V3
- [ ] 集成现有 Evaluator Agent 到 Evaluator V3
- [ ] 集成现有 Adoption Tracker 到 Adoption Tracker V3
- [ ] WebSocket 集成（通过配置开关切换 V2/V3）
- [ ] 指标埋点和测试

---

## 文件改动列表

### 新增文件（20个）

#### 文档
1. `docs/system_design/agentic_architecture_v3.md` - 系统设计文档
2. `docs/ops/model_gateway.md` - Model Gateway 配置指南
3. `docs/v3_refactoring_complete.md` - 本文件

#### Schema
4. `app/schemas/v3_agent_outputs.py` - V3 Agent 输出 Schema

#### Model Gateway
5. `app/services/model_gateway/__init__.py` - Package 初始化
6. `app/services/model_gateway/schemas.py` - Gateway Schema
7. `app/services/model_gateway/gateway.py` - Model Gateway 主入口
8. `app/services/model_gateway/router.py` - 模型路由器
9. `app/services/model_gateway/budget.py` - 预算管理器
10. `app/services/model_gateway/providers/__init__.py` - Provider Package
11. `app/services/model_gateway/providers/base.py` - Provider 基类
12. `app/services/model_gateway/providers/mock.py` - Mock Provider
13. `app/services/model_gateway/providers/openai_provider.py` - OpenAI Provider
14. `app/services/model_gateway/providers/qwen_provider.py` - Qwen Provider
15. `app/services/model_gateway/providers/deepseek_provider.py` - DeepSeek Provider

#### V3 Agents
16. `app/agents/v3/session_director_v3.py` - Session Director V3

#### V3 Orchestrator
17. `app/services/v3_orchestrator.py` - V3 双流编排器

### 修改文件（1个）

1. `app/core/config.py` - 已包含 QWEN_API_KEY, DEEPSEEK_API_KEY, AGENTIC_V3_ENABLED

---

## 新增配置项列表

### 环境变量

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `AGENTIC_V3_ENABLED` | bool | `false` | 是否启用 V3 架构 |
| `QWEN_API_KEY` | str | `None` | Qwen API Key（DashScope） |
| `DEEPSEEK_API_KEY` | str | `None` | DeepSeek API Key |
| `OPENAI_API_KEY` | str | `None` | OpenAI API Key（已存在） |
| `MODEL_BUDGET_SESSION_TOKENS` | int | `10000` | 会话预算 tokens |
| `MODEL_BUDGET_TURN_TOKENS` | int | `2000` | 每轮预算 tokens |
| `MODEL_BUDGET_EMERGENCY_RESERVE` | float | `0.1` | 紧急储备比例 |

### 配置示例（.env）

```bash
# V3 架构开关
AGENTIC_V3_ENABLED=true

# Provider API Keys
OPENAI_API_KEY=sk-...
QWEN_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...

# 预算配置（可选）
MODEL_BUDGET_SESSION_TOKENS=10000
MODEL_BUDGET_TURN_TOKENS=2000
MODEL_BUDGET_EMERGENCY_RESERVE=0.1
```

---

## 测试运行方式

### 1. 单元测试（Router）

```bash
# 测试路由决策
python -m pytest tests/test_model_router.py -v

# 预期结果：不同 routing_context 下选中正确模型
```

### 2. 集成测试（Fast Path）

```bash
# 测试 Fast Path 不被 Slow Path 阻塞
python -m pytest tests/test_v3_orchestrator.py::test_fast_path_not_blocked -v

# 预期结果：Fast Path <3s 返回，Slow Path 异步执行
```

### 3. Schema 测试

```bash
# 测试 Schema 校验
python -m pytest tests/test_v3_schemas.py -v

# 预期结果：所有 Schema 校验通过，失败触发重试/降级
```

### 4. Mock Provider 测试

```bash
# 使用 Mock Provider 测试（无需真实 API Key）
AGENTIC_V3_ENABLED=true python -m pytest tests/test_model_gateway.py -v

# 预期结果：所有调用使用 Mock Provider，返回模拟结果
```

### 5. Smoke 测试（V2 vs V3）

```bash
# 同时运行 V2 和 V3 的最小回归
AGENTIC_V3_ENABLED=false python -m pytest tests/test_orchestrator_v2.py -v
AGENTIC_V3_ENABLED=true python -m pytest tests/test_orchestrator_v3.py -v

# 预期结果：两者都能正常工作
```

---

## 风险与回滚方式

### 风险

1. **集成风险**：V3 Agent 实现尚未完全集成现有 Agent 逻辑
2. **性能风险**：双流架构可能增加复杂度，需要验证性能提升
3. **兼容性风险**：Schema 变更可能影响现有前端/API 契约

### 回滚方式

#### 方法 1: 配置开关（推荐）

```bash
# 回滚到 V2
export AGENTIC_V3_ENABLED=false
# 或修改 .env 文件
AGENTIC_V3_ENABLED=false
```

#### 方法 2: 代码回滚

如果配置开关不够，可以修改 `app/api/endpoints/websocket.py`：

```python
# 在 _process_user_message 中
if settings.AGENTIC_V3_ENABLED:
    # V3 逻辑
    result = await v3_orchestrator.process_turn(...)
else:
    # V2 逻辑（原有代码）
    result = await orchestrator.process_interaction(...)
```

#### 方法 3: Git 回滚

```bash
# 回滚到重构前的 commit
git checkout <previous-commit-hash>
```

### 回滚检查清单

- [ ] 确认 `AGENTIC_V3_ENABLED=false`
- [ ] 重启服务
- [ ] 验证 WebSocket 连接正常
- [ ] 验证 Turn Loop 正常工作
- [ ] 验证现有功能不受影响

---

## 下一步工作

### 优先级 P0（必须完成）

1. **集成现有 Agent**
   - 将 `app/agents/rag_agent.py` 集成到 Retriever V3
   - 将 `app/agents/npc_agent.py` 集成到 NPC Generator V3
   - 将 `app/agents/coach_agent.py` 集成到 Coach Generator V3
   - 将 `app/agents/evaluator_agent.py` 集成到 Evaluator V3
   - 将 `app/services/adoption_tracker.py` 集成到 Adoption Tracker V3

2. **WebSocket 集成**
   - 在 `app/api/endpoints/websocket.py` 中添加 V3 支持
   - 通过配置开关切换 V2/V3

3. **指标埋点**
   - TTFS（快路径）
   - Slow Path 总耗时
   - 每轮 tokens/cost
   - 路由命中率
   - 降级次数与原因

### 优先级 P1（重要）

4. **测试**
   - 单元测试：Router、Budget Manager
   - 集成测试：Fast Path、Slow Path
   - Schema 测试：校验失败处理

5. **性能优化**
   - Provider 连接池
   - 缓存策略（prompt cache、retrieval cache）

### 优先级 P2（可选）

6. **可观测性**
   - Prometheus metrics
   - 分布式追踪（trace_id）

7. **文档完善**
   - API 文档更新
   - 部署指南

---

## 架构验证指标

### 目标指标

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| Fast Path TTFS | <3s (P99) | 待测试 |
| Slow Path 延迟 | 5-30s | 待测试 |
| 每轮成本 | <$0.05 | 待测试 |
| Schema 校验通过率 | >99% | 待测试 |
| 路由命中率 | >80% | 待测试 |
| 降级次数 | <10% | 待测试 |

### 验证方法

1. **性能测试**：使用 Mock Provider 模拟不同场景
2. **成本测试**：记录每次调用的 tokens 和成本
3. **稳定性测试**：长时间运行，监控降级和错误率

---

## 总结

V3 架构重构已完成核心框架搭建：

✅ **已完成**：
- 系统设计文档和第一性原理
- Model Gateway + Router + Budget Manager
- 6-Agent Schema 定义
- Session Director V3
- V3 Orchestrator（双流架构）
- Provider 抽象（OpenAI/Qwen/DeepSeek/Mock）

⏳ **待完成**：
- 集成现有 Agent 实现
- WebSocket 集成
- 指标埋点和测试

**关键优势**：
1. **职责分离**：6-Agent 最小可分解集，单一职责
2. **快慢分离**：Fast Path <3s，Slow Path 异步
3. **多模型支持**：统一 Gateway，支持多 Provider
4. **预算控制**：硬预算，自动降级
5. **可演进性**：Schema 校验，可替换 Agent

**下一步**：按照优先级完成 Agent 集成和测试，验证架构收益。

