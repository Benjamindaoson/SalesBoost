# Memory Service API 规格（MVP 可验收版）

> 目标：把“记忆”从“说了什么”升级为“是否有效/是否合规/是否被采纳/可追溯来源”，并支持多 Agent 协作。本文档为 **API 合同**，用于对齐 PRD 的 MVP 验收。

---

## 0. 设计总则（做什么 → 为什么 → 怎么做）

- **做什么**：提供统一的 Memory Service API，用于写入事件/画像/知识/策略、路由检索、合规拦截、审计追溯、采纳闭环。
- **为什么（对齐 PRD）**：
  - 权益/活动/佣金回答必须准确且可追溯。
  - 异议处理/推进话术需提升采纳率（≥30%）。
  - 合规违规必须 100% 识别拦截并给替代表达。
  - 多 Agent 分工协作（知识库/NPC/教练/评估）。
- **怎么做（工程实现）**：
  - 三层记忆（Working / Persona / Global Expert）。
  - 双索引（语义索引 + 证据索引）。
  - 审计链（输入→路由→检索→证据→合规→输出）。
  - 合规优先级最高（输出前强制拦截）。

---

## 1. 角色与权限模型（RBAC + ABAC）

### 1.1 Agent 角色
- **knowledge-agent**：管理 Knowledge，读写全局知识，写审计。
- **npc-agent**：读 Persona/Strategy，写 Event（仅客户行为）。
- **coach-agent**：读 Working/Persona/Strategy，写 Event/Outcome。
- **evaluator-agent**：读全量 Event，写 Outcome/Persona（结构化评估）。

### 1.2 权限关键字段（所有请求必须携带）
- `tenant_id`：租户隔离
- `user_id`：用户维度
- `agent_role`：调用方角色
- `scope`：访问级别（例如 `public|team|private`）

---

## 2. 通用约定

### 2.1 统一 Header
- `X-Request-Id`：请求追踪 ID（必填）
- `X-Tenant-Id`：租户 ID（必填）
- `X-Agent-Role`：调用方角色（必填）
- `X-Idempotency-Key`：幂等键（强烈建议）

### 2.2 统一返回结构
```json
{
  "request_id": "req_123",
  "status": "ok",
  "data": {...},
  "error": null
}
```

### 2.3 错误码建议
- `400` 参数错误
- `403` 权限不足
- `409` 幂等冲突
- `422` 合规拦截（含替代表达）
- `500` 服务内部错误

---

## 3. 路由规则（硬约束）

**优先级顺序（强制）**
1. 合规拦截（输出前执行）
2. 权益/活动/佣金 → Knowledge + 结构化查询优先
3. 异议处理/SOP/推进 → StrategyUnit
4. 闲聊兜底（无业务影响）

Memory Service 在 `POST /memory/query` 内必须返回路由结果，且写入审计链。

---

## 4. API 列表

### 4.1 写入事件（Event）
**POST** `/memory/write/event`

**做什么**：写入对话/行为事件（可选写入向量索引）。
**为什么**：评估还原链路、采纳闭环、审计追溯。
**怎么做**：支持 `speaker`、`intent`、`stage`、`objection_type`、`compliance_flags`、`suggestions_shown/taken`。

**Request**
```json
{
  "event_id": "evt_123",
  "tenant_id": "t1",
  "user_id": "u1",
  "session_id": "s1",
  "channel": "voice",
  "turn_index": 12,
  "speaker": "sales|customer|npc|agent",
  "raw_text_ref": "enc://blob/xxx",
  "summary": "简要摘要",
  "intent_top1": "权益问答",
  "intent_topk": ["权益问答","合规风险"],
  "stage": "需求确认",
  "objection_type": "费用太高",
  "entities": ["卡种A","年费"],
  "sentiment": "neutral",
  "tension": 0.2,
  "compliance_flags": ["rule_32"],
  "coach_suggestions_shown": ["strategy_88"],
  "coach_suggestions_taken": ["strategy_88"],
  "metadata": {"locale": "zh-CN"}
}
```

**Response**
```json
{
  "request_id": "req_123",
  "status": "ok",
  "data": {"event_id": "evt_123", "stored": ["postgres", "vector"]},
  "error": null
}
```

---

### 4.2 写入 Outcome（采纳闭环）
**POST** `/memory/write/outcome`

**做什么**：写入采纳结果与推进结果。
**为什么**：采纳率 ≥30% 的闭环度量。
**怎么做**：绑定 `session_id` 与 `event_id`。

**Request**
```json
{
  "session_id": "s1",
  "event_id": "evt_123",
  "adopted": true,
  "adopt_type": "script|action_list",
  "stage_before": "需求确认",
  "stage_after": "异议处理",
  "eval_scores": {"stage_score": 0.78, "compliance": 1.0},
  "compliance_result": "pass|blocked",
  "final_result": "申请|首刷|流失"
}
```

---

### 4.3 写入 Persona（画像/成长）
**POST** `/memory/write/persona`

**做什么**：评估 Agent 写入结构化画像与成长记录。
**为什么**：对齐“分层差异化指导 + 成长追踪”。

**Request**
```json
{
  "user_id": "u1",
  "level": "新手|普通|成熟",
  "weakness_tags": ["异议处理", "合规表达"],
  "last_eval_summary": "简述",
  "last_improvements": ["结构更清晰"],
  "next_actions": ["加强A场景话术"],
  "history_stats": {"session_count": 12, "avg_score": 0.71}
}
```

---

### 4.4 写入 Knowledge（权益/活动/佣金/合规口径）
**POST** `/memory/write/knowledge`

**做什么**：新增/更新知识条款（强版本）。
**为什么**：保障回答准确与可追溯。

**Request**
```json
{
  "knowledge_id": "k_001",
  "domain": "权益|活动|佣金|合规",
  "product_id": "card_a",
  "structured_content": {"points": ["年费可减免"], "limits": ["需满足X" ]},
  "source_ref": "db://benefit_table#v3",
  "version": "2026-01-20",
  "effective_from": "2026-01-20",
  "effective_to": null,
  "is_enabled": true,
  "citation_snippets": ["满足X条件可减免"]
}
```

---

### 4.5 写入 StrategyUnit（销冠策略单元）
**POST** `/memory/write/strategy`

**做什么**：写入销冠策略/异议处理/合规替代表达。
**为什么**：提升采纳率与推进率。

**Request**
```json
{
  "strategy_id": "strategy_88",
  "type": "SOP|异议|推进|合规替代",
  "trigger_condition": {
    "intent": "异议处理",
    "stage": "需求确认",
    "objection_type": "费用太高",
    "level": "新手"
  },
  "steps": ["共情", "澄清条件", "提供替代表达"],
  "scripts": ["如果您在意年费..."],
  "dos_donts": {"dos": ["说明限制"], "donts": ["保证收益"]},
  "evidence_event_ids": ["evt_123"],
  "stats": {"adoption_rate": 0.31, "progress_rate": 0.22, "risk_rate": 0.02}
}
```

---

### 4.6 查询（统一路由 + 检索）
**POST** `/memory/query`

**做什么**：统一入口，执行意图路由与检索。
**为什么**：满足“准确、快、可追溯、合规 100%”。
**怎么做**：强制返回 `route_decision` 与 `citations`，并写审计。

**Request**
```json
{
  "query": "年费怎么减免？",
  "tenant_id": "t1",
  "user_id": "u1",
  "session_id": "s1",
  "intent_hint": "权益问答",
  "stage": "需求确认",
  "objection_type": null,
  "top_k": 5,
  "require_citations": true,
  "route_policy": "compliance>knowledge>strategy>fallback"
}
```

**Response**
```json
{
  "request_id": "req_123",
  "status": "ok",
  "data": {
    "route_decision": "knowledge",
    "hits": [
      {
        "type": "knowledge",
        "id": "k_001",
        "score": 0.91,
        "content": {"points": ["年费可减免"]}
      }
    ],
    "citations": [
      {"type": "knowledge", "id": "k_001", "version": "2026-01-20", "snippet": "满足X条件可减免", "source_ref": "db://benefit_table#v3"}
    ]
  },
  "error": null
}
```

---

### 4.7 合规拦截（输出前强制）
**POST** `/memory/comply/check`

**做什么**：对候选输出进行强制合规校验并给替代表达。
**为什么**：100% 识别拦截与替代。
**怎么做**：若 `blocked` 必须返回 `safe_response`，并写入审计。

**Request**
```json
{
  "request_id": "req_123",
  "session_id": "s1",
  "candidate_response": "保证收益100%",
  "citations": [
    {"type": "knowledge", "id": "k_001", "version": "2026-01-20"}
  ]
}
```

**Response（阻断）**
```json
{
  "request_id": "req_123",
  "status": "blocked",
  "data": {
    "action": "rewrite",
    "hits": [{"rule_id": "rule_32", "reason": "禁止承诺收益"}],
    "safe_response": "根据规定不能承诺收益，我可以说明申请条件与权益范围。"
  },
  "error": null
}
```

---

### 4.8 审计追溯（Audit Trace）
**POST** `/memory/trace`

**做什么**：获取一次请求的完整审计链。
**为什么**：满足抽检与可追溯。

**Request**
```json
{ "request_id": "req_123" }
```

**Response**
```json
{
  "request_id": "req_123",
  "status": "ok",
  "data": {
    "input_digest": "sha256:...",
    "route": "knowledge",
    "retrieved_ids": ["k_001"],
    "citations": [{"type":"knowledge","id":"k_001","version":"2026-01-20"}],
    "compliance_hits": ["rule_32"],
    "output_digest": "sha256:..."
  },
  "error": null
}
```

---

## 5. 证据与可追溯（强约束）

每次 **回答/建议** 必须带 `citations`：
- Knowledge：`knowledge_id + version + source_ref`
- Strategy：`strategy_id + evidence_event_id`
- Compliance：`rule_id + policy_version`

服务端必须将 `citations` 写入 Audit。

---

## 6. 合规优先级（强约束）

- 合规检查必须在最终输出前执行。
- 若命中规则，必须返回替代表达。
- 所有命中写入 Audit。失败直接 `422`。

---

## 7. 采纳闭环（强约束）

- 对话中：Event 记录建议展示/采纳信号。
- 对话后：Outcome 写入采纳与推进结果。
- StrategyUnit 统计更新（adoption_rate / progress_rate / risk_rate）。

---

## 8. 备注（与现有系统对齐）

- Redis：Working Memory + 热点缓存 + 事件总线
- Chroma/Qdrant：向量召回（统一接口）
- Postgres：主存储与审计
- 事件总线：异步写入向量与统计更新

---

## 9. MVP 验收映射（快速对齐）

- 权益问答准确 ≥95%：`/memory/query` + Knowledge 强版本 + citations
- 采纳率 ≥30%：`/memory/write/outcome` + StrategyUnit 统计
- 合规拦截 100%：`/memory/comply/check`
- 可追溯：`/memory/trace`

---

> 下一步：如果本 API 通过，即可输出 PostgreSQL DDL + Qdrant Collection 设计，保证字段与索引一致。
