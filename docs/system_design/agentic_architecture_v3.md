# Agentic Architecture V3 - 系统设计文档

## 0. 第一性原理

### 0.1 系统目标函数（Optimization Objective）

在保证销售训练"决策质量与一致性"的前提下，最小化：

1. **P99 延迟（尤其 TTFS）**
   - 目标：快路径 TTFS < 3s（P99）
   - 慢路径允许 5-30s 异步推送

2. **单轮成本（tokens + 调用次数）**
   - 目标：每轮成本 < $0.05（基于 OpenAI GPT-4 定价）
   - 通过模型路由和降级策略控制

3. **不可控性（prompt 漂移、评估不稳定、耦合导致的不可替换）**
   - 目标：Schema 校验通过率 > 99%
   - Agent 可独立替换，不影响其他模块

并最大化：

1. **行为可度量性（建议→采纳→skill_delta 因果链）**
   - 目标：采纳追踪覆盖率 100%
   - skill_delta 计算准确率 > 95%

2. **可演进性（替换模型/评估器/检索器不影响其他模块）**
   - 目标：通过 Model Gateway 抽象，支持多 Provider
   - Agent 接口标准化，可插拔

3. **可扩展性（多副本 WS / 异步处理 / 可观测）**
   - 目标：支持水平扩展（多实例）
   - 异步处理不阻塞主流程

### 0.2 系统不变量（Non-negotiables）

1. **控制层/执行层/裁判层必须分离**
   - Controller（Session Director）不能生成内容
   - Evaluator 不能当教练
   - NPC 不能输出教练建议

2. **快慢分离**
   - 快路径必须可在 <3s TTFS 返回 NPC 回复
   - 慢路径允许 5-30s 异步推送建议与评估

3. **可审计输出**
   - Coach/Eval 必须输出结构化 JSON（schema 校验 + 失败自动修复/降级）

4. **硬预算**
   - 每轮/每会话有成本与延迟上限
   - 超限必须降级（GraphRAG→Vector-only；强模型→便宜模型；评估频率下降）

---

## 1. 目标架构：6-Agent 最小可分解集

### 1.1 Session Director（控制器）

**职责**：
- 输入：FSM state、turn context、预算、风险、证据置信度
- 输出：turn_plan（本轮走快/慢、调用哪些 agent、预算、是否升级模型）

**约束**：
- 不生成内容，只做决策
- 基于预算和风险选择模型和路径

### 1.2 Retriever（证据构造器）

**职责**：
- 只产出 evidence_pack（facts/policies/objection_playbooks/graph_insights/confidence）
- 快路径只允许 lightweight vector retrieval + rerank
- GraphRAG 只允许慢路径，且必须有 Hard Budget（节点数/深度/时间）

**约束**：
- 快路径：向量检索 + rerank（<1s）
- 慢路径：GraphRAG（5-30s，有预算限制）

### 1.3 NPC Generator（客户模拟器）

**职责**：
- 只输出 npc_reply（受 persona + FSM 阶段约束）
- 不包含教练/评估内容

**约束**：
- 必须走快路径
- 输出结构化，可校验

### 1.4 Coach Generator（教练）

**职责**：
- 输出结构化 coach_advice（why/action/suggested_reply/alternatives/guardrails）

**约束**：
- 只走慢路径
- Schema 校验失败自动修复/降级

### 1.5 Evaluator（裁判）

**职责**：
- 输出结构化 evaluation（scores/rationales/error_tags/compliance_flags/stage_mistakes）
- 一致性优先（固定温度/尽量固定模型）

**约束**：
- 只走慢路径
- 评估结果可审计

### 1.6 Adoption & Attribution Tracker（采纳归因器）

**职责**：
- 追踪建议是否被采纳
- 计算 skill_delta
- 写入可用于训练与成长追踪的数据结构

**约束**：
- 只走慢路径
- 数据必须可追溯

---

## 2. 双流架构（Fast Path / Slow Path）

### 2.1 Fast Path（必须保障 TTFS）

**执行顺序**：
```
Session Director → Retriever(light) 并行 → NPC Generator → 返回 NPC 回复
```

**目标**：
- TTFS < 3s（在本地/测试环境至少能验证"不会被慢任务阻塞"）

**包含 Agent**：
- Session Director（决策）
- Retriever（轻量检索）
- NPC Generator（生成回复）

### 2.2 Slow Path（异步）

**执行顺序**：
```
Retriever(GraphRAG 可选) → Coach → Evaluator → Adoption Tracker → WebSocket 推送侧边栏消息
```

**要求**：
- Slow Path 失败不影响主对话
- Slow Path 可重试、可降级、可观测

**包含 Agent**：
- Retriever（GraphRAG，可选）
- Coach Generator
- Evaluator
- Adoption Tracker

---

## 3. 多模型路由

### 3.1 Model Gateway 架构

```
Model Gateway
├── Providers (OpenAI/Qwen/DeepSeek)
├── Router (按 agent_type + turn_importance + risk + budget_remaining + latency_mode + retrieval_confidence)
├── Budget Manager
├── Circuit Breaker
└── Cache (prompt cache + retrieval cache)
```

### 3.2 路由策略

**按 Agent Type**：
- NPC Generator：优先 Qwen（成本低，质量可接受）
- Coach Generator：优先 OpenAI GPT-4（质量要求高）
- Evaluator：固定 OpenAI GPT-4（一致性要求）
- Retriever：优先 DeepSeek（embedding 成本低）

**按 Turn Importance**：
- 关键轮次（如 CLOSING）：升级到强模型
- 普通轮次：使用便宜模型

**按 Budget**：
- 预算充足：使用强模型
- 预算不足：降级到便宜模型

**按 Latency Mode**：
- Fast Path：优先快速模型
- Slow Path：允许慢速但高质量模型

### 3.3 降级策略

1. **超时降级**：>5s 自动切换到快速模型
2. **错误降级**：Provider 错误自动切换
3. **预算降级**：预算不足自动降级
4. **置信度降级**：检索置信度低时降级

---

## 4. 数据结构与协议

### 4.1 结构化 I/O Schema

所有 Agent 输出必须符合以下 Schema：

- `TurnPlan`：Session Director 输出
- `EvidencePack`：Retriever 输出
- `NpcReply`：NPC Generator 输出
- `CoachAdvice`：Coach Generator 输出
- `Evaluation`：Evaluator 输出
- `AdoptionLog`：Adoption Tracker 输出

### 4.2 Schema 校验失败处理

1. **修复重试**：使用便宜模型尝试修复
2. **降级输出**：修复失败则输出降级版本（保证系统稳定）

---

## 5. 与现有系统集成

### 5.1 约束

- 不改变现有 API 契约（除非同时改前端与测试）
- 不破坏 WebSocket 主流程
- 保持已有 FSM 协议不变

### 5.2 迁移策略

- 新架构以 v3 命名，不直接删除旧逻辑
- 通过配置开关切换（`AGENTIC_V3_ENABLED=true`）
- 在 CI/测试中同时跑 v2 与 v3 的最小回归（至少 smoke）

---

## 6. 可验证"更好"：指标与测试

### 6.1 指标埋点

- TTFS（快路径）
- Slow Path 总耗时
- 每轮 tokens/cost
- 路由命中率（便宜模型 vs 强模型占比）
- 降级次数与原因（timeout/budget/low_confidence）

### 6.2 测试

- **单元测试**：Router 在不同 routing_context 下选中正确模型
- **集成测试**：Fast Path 不被 Slow Path 阻塞
- **Schema 测试**：Coach/Eval 输出必须能通过校验；失败触发重试/降级

---

## 7. 与需求映射表

| 需求 | V3 实现 |
|------|---------|
| 实时辅助（一句话话术） | Fast Path NPC + Slow Path Coach |
| 合规兜底 | Evaluator 输出 compliance_flags |
| 轻量复盘 | Evaluator + Adoption Tracker |
| 多模型支持 | Model Gateway + Router |
| 成本控制 | Budget Manager |
| 可扩展性 | 双流架构 + 异步处理 |

---

## 8. 架构图（文字描述）

```
用户消息
    ↓
Session Director (决策：快/慢路径、模型选择、预算分配)
    ↓
    ├─→ Fast Path (<3s)
    │   ├─→ Retriever(light) ──┐
    │   │                        ↓
    │   └─→ NPC Generator ──→ 返回 NPC 回复
    │
    └─→ Slow Path (异步，5-30s)
        ├─→ Retriever(GraphRAG, 可选)
        ├─→ Coach Generator ──→ 推送建议
        ├─→ Evaluator ──→ 推送评估
        └─→ Adoption Tracker ──→ 更新采纳数据
```

---

## 9. 时序图

```
用户 → WebSocket → Session Director
                    ↓
            [Fast Path]
            ├─ Retriever(light) ──┐
            │                     ↓
            └─ NPC Generator ──→ 返回 NPC 回复 (<3s)
            
            [Slow Path] (异步)
            ├─ Retriever(GraphRAG) ──┐
            │                        ↓
            ├─ Coach Generator ──→ 推送建议
            ├─ Evaluator ──→ 推送评估
            └─ Adoption Tracker ──→ 更新数据
```

---

## 10. 预算策略

### 10.1 每轮预算

- 默认：$0.05/轮
- Fast Path：$0.02/轮
- Slow Path：$0.03/轮

### 10.2 每会话预算

- 默认：$1.00/会话
- 超限自动降级

### 10.3 预算扣减

- 每次模型调用扣减对应成本
- 实时监控，超限预警

---

## 11. 降级策略

### 11.1 超时降级

- Fast Path >3s：降级到最快模型
- Slow Path >30s：降级到便宜模型

### 11.2 错误降级

- Provider 错误：自动切换 Provider
- Schema 校验失败：修复重试 → 降级输出

### 11.3 预算降级

- 预算不足：优先使用便宜模型
- 预算耗尽：停止非必要调用

---

## 12. 可观测性

### 12.1 日志

- 每次 Agent 调用记录日志
- 包含：agent_type、model、tokens、cost、latency、success/failure

### 12.2 指标

- Prometheus metrics（可选）
- 自定义指标：TTFS、成本、降级次数

### 12.3 追踪

- 每轮请求分配 trace_id
- 追踪完整调用链
