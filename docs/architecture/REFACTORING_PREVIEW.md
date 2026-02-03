# SalesBoost 架构重排预览方案

**重构原则**: 从"技术分层"演进为"智能体认知层级"  
**重构日期**: 2026-01-27  
**状态**: 预览阶段（待确认后执行）

---

## 📋 一、目标架构蓝图

```
app/
├── engine/                    # 🧠 大脑中心 - 推理与执行工程
│   ├── intent/                # 意图识别门卫
│   ├── coordinator/           # 角色编排与路径决策
│   └── state/                 # 状态管理（FSM + 上下文快照）
│
├── agents/                    # 🎯 技能执行层 - PRD 业务对齐
│   ├── study/                 # 「学」- 知识检索、RAG
│   ├── ask/                   # 「问」- 实时辅助、话术建议
│   ├── practice/              # 「练」- NPC 模拟、教练纠偏
│   └── evaluate/              # 「评」- 量化评估、博弈风格分析
│
├── memory/                    # 💾 记忆资产层 - 认知持久化
│   ├── context/               # 短期记忆（影子摘要、上下文压缩）
│   ├── tracking/              # 长线追踪（待办任务、能力成长）
│   └── storage/               # 持久化记忆（用户画像向量库）
│
├── tools/                     # 🛠️ 肢体扩展层 - 工具调用
│   ├── parsers/               # 内容解析工具（OCR, MinerU）
│   └── connectors/            # 外部系统/API 适配器
│
├── infra/                     # ⚙️ 基础设施层 - 底座与治理
│   ├── gateway/               # 统一模型网关、计费、路由决策
│   ├── guardrails/            # 安全卫士（滑动窗口扫描、合规过滤）
│   └── providers/             # 厂商 SDK 适配
│
└── observability/             # 📊 反馈工程 - 可观测性
    ├── tracing/               # 异步 Trace 记录
    └── metrics/               # 业务 KPI 指标采集
```

---

## 📦 二、文件搬迁映射表

### 2.1 Engine 层（大脑中心）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/engine/orchestrator.py` | `app/engine/coordinator/workflow_coordinator.py` | ✅ | 核心编排逻辑，负责"分解目标与下发任务" |
| `app/engine/coordinator.py` | `app/engine/coordinator/session_coordinator.py` | ✅ | 会话状态协调，属于编排层 |
| `app/engine/router.py` | `app/engine/coordinator/path_router.py` | ✅ | 路径决策（Fast/Slow），属于编排决策 |
| `app/agents/ask/intent_gate.py` | `app/engine/intent/intent_gateway.py` | ✅ | 意图识别门卫，负责"认清客户在干嘛" |
| `app/agents/ask/session_director_v3.py` | `app/engine/coordinator/session_director.py` | ✅ | 会话规划，属于编排决策层 |
| `app/fsm/engine.py` | `app/engine/state/fsm_engine.py` | ✅ | FSM 状态机，属于状态管理 |
| `app/fsm/decision_engine.py` | `app/engine/state/transition_decision.py` | ✅ | 状态转换决策，属于状态管理 |
| `app/services/state/wal.py` | `app/engine/state/wal.py` | ✅ | 写前日志，状态持久化 |
| `app/services/state_snapshot.py` | `app/engine/state/snapshot.py` | ✅ | 状态快照，状态管理 |
| `app/services/simple_state_snapshot.py` | `app/engine/state/simple_snapshot.py` | ✅ | 简化状态快照 |
| `app/services/state_recovery.py` | `app/engine/state/recovery.py` | ✅ | 状态恢复，状态管理 |
| `app/services/state_updater.py` | `app/engine/state/updater.py` | ✅ | 状态更新，状态管理 |

### 2.2 Agents 层（技能执行层）

#### Study（学）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/agents/study/retriever_v3.py` | `app/agents/study/knowledge_retriever.py` | ✅ | 知识检索，核心"学"功能 |
| `app/services/knowledge_engine.py` | `app/agents/study/knowledge_engine.py` | ✅ | 知识引擎，支撑"学" |
| `app/services/knowledge_service.py` | `app/agents/study/knowledge_service.py` | ✅ | 知识服务，支撑"学" |
| `app/services/knowledge_service_qdrant.py` | `app/agents/study/qdrant_service.py` | ✅ | Qdrant 知识服务 |
| `app/services/advanced_rag/` | `app/agents/study/advanced_rag/` | - | 高级 RAG，属于"学" |
| `app/services/graph_rag/` | `app/agents/study/graph_rag/` | - | GraphRAG，属于"学" |
| `app/services/graph_rag_service.py` | `app/agents/study/graph_rag_service.py` | ✅ | GraphRAG 服务 |
| `app/services/advanced_rag_service.py` | `app/agents/study/advanced_rag_service.py` | ✅ | 高级 RAG 服务 |
| `app/services/retrieval_control_plane/` | `app/agents/study/retrieval_control/` | - | 检索控制平面 |
| `app/services/semantic_cache.py` | `app/agents/study/semantic_cache.py` | ✅ | 语义缓存，支撑检索 |

#### Ask（问）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/quick_suggest_service.py` | `app/agents/ask/quick_suggest.py` | ✅ | 快速建议，属于"问" |
| `app/services/intent_classifier.py` | `app/agents/ask/intent_classifier.py` | ✅ | 意图分类，支撑"问" |

#### Practice（练）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/agents/practice/npc_generator_v3.py` | `app/agents/practice/npc_generator.py` | ✅ | NPC 生成器，核心"练"功能 |
| `app/agents/practice/coach_generator_v3.py` | `app/agents/practice/coach_generator.py` | ✅ | 教练生成器，核心"练"功能 |
| `app/agents/practice/npc_agent.py` | `app/agents/practice/npc_agent.py` | - | NPC Agent（保留） |
| `app/agents/practice/coach_agent.py` | `app/agents/practice/coach_agent.py` | - | Coach Agent（保留） |

#### Evaluate（评）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/agents/evaluate/evaluator_v3.py` | `app/agents/evaluate/evaluator.py` | ✅ | 评估器，核心"评"功能 |
| `app/agents/evaluate/evaluator_agent.py` | `app/agents/evaluate/base_evaluator.py` | ✅ | 基础评估器 |
| `app/agents/evaluate/style_evaluator.py` | `app/agents/evaluate/game_style_analyzer.py` | ✅ | 博弈风格分析器 |
| `app/agents/evaluate/adoption_tracker_v3.py` | `app/agents/evaluate/adoption_tracker.py` | ✅ | 采纳追踪器 |
| `app/services/adoption_tracker.py` | `app/agents/evaluate/adoption_service.py` | ✅ | 采纳服务（底层） |
| `app/services/strategy_analyzer.py` | `app/agents/evaluate/strategy_analyzer.py` | ✅ | 策略分析器 |
| `app/services/curriculum_planner.py` | `app/agents/evaluate/curriculum_planner.py` | ✅ | 课程规划器 |
| `app/services/report_service.py` | `app/agents/evaluate/report_generator.py` | ✅ | 报告生成器 |

### 2.3 Memory 层（记忆资产层）

#### Context（短期记忆）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/shadow_summarizer.py` | `app/memory/context/shadow_summarizer.py` | ✅ | 影子摘要，短期记忆 |
| `app/services/context_engine.py` | `app/memory/context/context_engine.py` | ✅ | 上下文引擎，短期记忆 |
| `app/services/context_compressor.py` | `app/memory/context/compressor.py` | ✅ | 上下文压缩 |

#### Tracking（长线追踪）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/followup_manager.py` | `app/memory/tracking/followup_manager.py` | ✅ | 待办任务追踪 |
| `app/services/progression_service.py` | `app/memory/tracking/progression_tracker.py` | ✅ | 能力成长追踪 |
| `app/services/memory_metrics_service.py` | `app/memory/tracking/metrics.py` | ✅ | 记忆指标追踪 |

#### Storage（持久化记忆）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/memory_service.py` | `app/memory/storage/profile_service.py` | ✅ | 用户画像服务 |
| `app/services/memory_read_service.py` | `app/memory/storage/read_service.py` | ✅ | 记忆读取服务 |
| `app/services/memory_write_service.py` | `app/memory/storage/write_service.py` | ✅ | 记忆写入服务 |
| `app/services/memory_event_store.py` | `app/memory/storage/event_store.py` | ✅ | 记忆事件存储 |
| `app/services/memory/` | `app/memory/storage/backends/` | - | 存储后端实现 |

### 2.4 Tools 层（肢体扩展层）

#### Parsers（内容解析）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/infra/parsers/document_parser.py` | `app/tools/parsers/document_parser.py` | ✅ | 文档解析器 |
| `app/infra/parsers/enhanced_document_parser.py` | `app/tools/parsers/enhanced_parser.py` | ✅ | 增强解析器 |

#### Connectors（外部适配）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/multimodal/` | `app/tools/connectors/multimodal/` | - | 多模态连接器 |
| `app/services/ingestion/` | `app/tools/connectors/ingestion/` | - | 数据摄取连接器 |

### 2.5 Infra 层（基础设施层）

#### Gateway（模型网关）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/model_gateway/` | `app/infra/gateway/` | - | 统一模型网关 |
| `app/services/model_gateway/budget.py` | `app/infra/gateway/budget.py` | ✅ | 预算管理 |
| `app/services/model_gateway/gateway.py` | `app/infra/gateway/gateway.py` | ✅ | 网关核心 |
| `app/services/model_gateway/router.py` | `app/infra/gateway/router.py` | ✅ | 路由决策 |
| `app/services/model_gateway/router_rulebook.py` | `app/infra/gateway/rulebook.py` | ✅ | 路由规则书 |
| `app/services/model_gateway/schemas.py` | `app/infra/gateway/schemas.py` | ✅ | 网关 Schema |
| `app/services/model_gateway/providers/` | `app/infra/providers/` | - | 厂商 SDK 适配 |
| `app/services/llm_service.py` | `app/infra/gateway/llm_service.py` | ✅ | LLM 服务（网关封装） |
| `app/services/cost_control.py` | `app/infra/gateway/cost_control.py` | ✅ | 成本控制 |

#### Guardrails（安全卫士）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/security/runtime_guard.py` | `app/infra/guardrails/runtime_guard.py` | ✅ | 运行时安全卫士 |
| `app/security/injection_guard.py` | `app/infra/guardrails/injection_guard.py` | ✅ | 注入防护 |
| `app/security/prompt_guard.py` | `app/infra/guardrails/prompt_guard.py` | ✅ | Prompt 防护 |
| `app/services/compliance_engine.py` | `app/infra/guardrails/compliance_engine.py` | ✅ | 合规引擎 |
| `app/agents/roles/compliance_agent.py` | `app/infra/guardrails/compliance_agent.py` | ✅ | 合规 Agent |

### 2.6 Observability 层（反馈工程）

#### Tracing（异步 Trace）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/observability/trace_manager.py` | `app/observability/tracing/trace_manager.py` | ✅ | Trace 管理器 |
| `app/schemas/trace.py` | `app/observability/tracing/schemas.py` | ✅ | Trace Schema |

#### Metrics（业务 KPI）

| 当前路径 | 新路径 | 重命名 | 搬迁理由 |
|---------|--------|--------|---------|
| `app/services/performance_metrics.py` | `app/observability/metrics/performance.py` | ✅ | 性能指标 |
| `app/services/observability/metrics.py` | `app/observability/metrics/system.py` | ✅ | 系统指标 |

---

## 🗑️ 三、冗余文件清理清单

### 3.1 已废弃的 V1/V2 遗留

| 文件路径 | 状态 | 清理理由 |
|---------|------|---------|
| `app/agents/v3/enhanced_v3_orchestrator.py` | ❌ 删除 | 已被 `workflow_coordinator.py` 替代 |
| `app/agents/v3/enhanced_intent_gate.py` | ❌ 删除 | 已被 `intent_gateway.py` 替代 |
| `app/agents/v3/simple_intent_gate.py` | ❌ 删除 | 已被 `intent_gateway.py` 替代 |
| `app/agents/v3/simplified_intent_gate.py` | ❌ 删除 | 已被 `intent_gateway.py` 替代 |
| `app/services/enhanced_task_registry.py` | ❌ 删除 | 已被 `workflow_coordinator.py` 中的 `TaskRegistry` 替代 |
| `app/services/enhanced_task_registry_fixed.py` | ❌ 删除 | 已被 `workflow_coordinator.py` 中的 `TaskRegistry` 替代 |

### 3.2 空目录清理

- `app/agents/coordination/` (已删除)
- `app/agents/roles/` (部分文件已迁移，检查是否为空)

---

## 📝 四、关键文件搬迁逻辑说明

### 4.1 Orchestrator → Workflow Coordinator

**搬迁理由**:
- `orchestrator.py` 是系统的"大脑"，负责协调所有 Agent 的执行
- 它实现了"学问练评"工作流，属于"角色编排与路径决策"层
- 重命名为 `workflow_coordinator.py` 更清晰地表达其职责

**影响范围**:
- `app/api/endpoints/websocket.py` 中的导入
- `app/main.py` 中的初始化
- 所有调用 `SalesOrchestrator` 的地方

### 4.2 Retriever → Knowledge Retriever

**搬迁理由**:
- `retriever_v3.py` 是"学"环节的核心组件
- 负责知识检索与证据构造，属于技能执行层
- 移除 `_v3` 后缀，使用语义化命名

### 4.3 Style Evaluator → Game Style Analyzer

**搬迁理由**:
- `style_evaluator.py` 负责博弈风格分析
- 名称更清晰地表达其分析功能
- 属于"评"环节的组件

### 4.4 Model Gateway → Infra Gateway

**搬迁理由**:
- 模型网关是基础设施层，不属于业务逻辑
- 统一管理所有 LLM 调用、计费、路由
- 属于"底座与治理"层

### 4.5 Security → Guardrails

**搬迁理由**:
- 安全组件是基础设施层的"卫士"
- 负责运行时防护、合规检查
- 重命名为 `guardrails` 更符合其"护栏"职责

---

## ⚠️ 五、重构风险与注意事项

### 5.1 高风险变更

1. **Orchestrator 重命名**
   - 影响范围：所有 API 端点、WebSocket 处理
   - 需要全局搜索替换 `SalesOrchestrator` → `WorkflowCoordinator`

2. **Model Gateway 路径变更**
   - 影响范围：40+ 文件导入 `app.services.model_gateway`
   - 需要批量替换为 `app.infra.gateway`

3. **Memory Service 拆分**
   - 影响范围：所有使用 `memory_service` 的地方
   - 需要区分 `profile_service`、`read_service`、`write_service`

### 5.2 依赖关系检查

- ✅ 检查所有 `from app.services.model_gateway` 的导入
- ✅ 检查所有 `from app.engine.orchestrator` 的导入
- ✅ 检查所有 `from app.security` 的导入
- ✅ 检查所有 `from app.services.memory` 的导入

### 5.3 测试覆盖

重构后需要验证：
- [ ] WebSocket 连接正常
- [ ] 所有 Agent 调用正常
- [ ] 模型网关路由正常
- [ ] 状态管理正常
- [ ] 记忆服务正常

---

## ✅ 六、执行检查清单

### 阶段 1: 预览确认
- [x] 生成重构预览文档
- [ ] **等待用户确认后执行**

### 阶段 2: 物理搬迁
- [ ] 创建新目录结构
- [ ] 移动文件到新位置
- [ ] 重命名文件
- [ ] 删除冗余文件

### 阶段 3: Import 修复
- [ ] 全局搜索替换导入路径
- [ ] 修复相对导入
- [ ] 更新 `__init__.py` 文件

### 阶段 4: 验证
- [ ] 运行 Linter 检查
- [ ] 运行类型检查
- [ ] 执行单元测试
- [ ] 手动测试关键流程

---

## 📊 七、重构统计

- **总文件数**: ~150 个 Python 文件
- **需要移动**: ~80 个文件
- **需要重命名**: ~40 个文件
- **需要删除**: ~6 个冗余文件
- **Import 路径变更**: ~200+ 处

---

**下一步**: 请确认此预览方案，确认后将开始执行物理搬迁与 Import 修复。
