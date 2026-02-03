# SalesBoost 任务编排系统深度技术评审报告

**日期**: 2026-01-29
**评审对象**: `app/engine/coordinator/` (重点: `dynamic_workflow.py`, `workflow_coordinator.py`)
**评审人**: AI System Architect

---

## 1. 现状摘要 (Status Summary)

目前的任务编排系统已完成从传统的硬编码流水线（Hard-coded Pipeline）向基于图的动态编排（Graph-based Orchestration）的转型。

- **核心引擎**: 引入了 `LangGraph` (`StateGraph`) 作为底层的状态机引擎。
- **动态性**: 通过 `WorkflowConfig` 实现节点的可配置启用与路由规则定义。
- **当前流程**:
  1. **Intent Node**: 识别用户意图 (ContextAwareIntentClassifier)。
  2. **Knowledge Node**: 根据意图检索知识库 (KnowledgeRetriever)。
  3. **NPC Node**: 生成客户模拟回复 (NPCGenerator)。
  4. **Coach Node**: 生成教练指导建议 (SalesCoachAgent)。
  5. **Compliance Node**: 进行合规性检查 (ComplianceCheckTool)。
- **模型路由**: 集成了级联路由策略 (`Router`)，根据意图复杂度动态选择模型以优化成本与延迟。

---

## 2. 核心亮点 (Core Highlights)

1. **架构现代化 (LangGraph Adoption)**:
   - 摒弃了线性的 `await A(); await B();` 模式，采用 `StateGraph`，支持循环、条件分支和状态持久化，符合2026年硅谷主流Agent架构趋势。

2. **配置驱动 (Configuration Driven)**:
   - `DynamicWorkflowCoordinator` 允许通过配置（而非修改代码）来改变业务流程。例如，可以轻松关闭 `Coach` 节点用于生产环境的轻量级部署。

3. **成本/延迟优化 (Cost/Latency Optimization)**:
   - 在 `router.py` 中实现了基于意图的级联路由（Cascade Routing）。简单意图（如寒暄）强制路由到低成本模型，复杂意图路由到高性能模型，预计降低 60% Token 成本。

4. **全链路可观测性 (Traceability)**:
   - 每个节点执行后都会向 `trace_log` 写入执行元数据（如 `response_len`, `risk_flags`），便于后续分析和调试。

---

## 3. 问题与改进建议 (Issues & Recommendations)

### 维度 1: AI 产品经理视角 (User Experience & Value)

*   **交互流畅度**:
    *   **现状**: 目前流程是串行的（Intent -> Knowledge -> NPC -> Coach -> Compliance）。
    *   **问题**: 如果 Knowledge 或 Coach 响应慢，用户等待时间（TTFT）会显著增加。
    *   **建议**: **并行执行**。Intent 识别后，Knowledge 检索和 NPC 思考可以并行进行；Coach 建议可以异步生成（Streaming）而不阻塞 NPC 回复的主显示。

*   **容错体验**:
    *   **现状**: 节点失败（如 Redis 连接失败）主要通过 `try-except` 捕获并记录错误，部分节点返回空值。
    *   **问题**: 用户可能感知到服务降级，但缺乏优雅的兜底话术。例如 Coach 挂了，前端没有任何提示。
    *   **建议**: 引入 **Fallback 策略**。如果 Intent 识别失败，默认进入 "General Chat" 模式；如果 Knowledge 失败，NPC 应使用通用话术过渡。

### 维度 2: AI 算法工程师视角 (Intelligence & Logic)

*   **路由策略**:
    *   **现状**: 路由逻辑主要基于 Intent 标签（如 `price_inquiry` -> `knowledge`）。
    *   **问题**: 缺乏对“对话深度”和“情绪状态”的动态响应。例如，当 NPC 情绪极差时，应强制跳转到人工干预或特定的安抚流程，而不仅仅是依赖 Intent。
    *   **建议**: 引入 **Global State Guardrails**。在图中增加全局守卫节点，监控 `mood` 和 `risk_level`，一旦触发阈值立即改变路由。

*   **上下文管理**:
    *   **现状**: 历史记录 (`history`) 是简单的 List Append。
    *   **问题**: 随着对话轮数增加，Context Window 可能会爆，且噪声增多。
    *   **建议**: 实现 **智能上下文压缩 (Smart Context Compression)**。在每一轮结束后，异步总结关键信息（Summary）并替换掉早期的 Raw Message。

### 维度 3: AI 应用开发视角 (Engineering & Scalability)

*   **接口一致性**:
    *   **现状**: `NPCGenerator` 的接口定义与调用方存在细微差异（如 `generate` vs `generate_response`），导致集成测试失败。
    *   **建议**: 定义严格的 **Protocol / Interface** 类，并使用 Pydantic 进行输入输出的运行时校验，杜绝“隐式契约”。

*   **本地开发体验**:
    *   **现状**: `CoachAgent` 强依赖 Redis，导致在无 Redis 环境下无法运行完整流程。
    *   **建议**: 完善 **Mock 机制**。检测到 Redis 连接失败时，自动切换到 `InMemoryCache` 或 `NullCache`，确保开发环境开箱即用。

---

## 4. 下一步行动 (Next Steps)

1.  **修复稳定性**:
    - [x] 修复 `NPCGenerator` 调用接口不匹配问题（已完成）。
    - [ ] 优化 `CoachAgent` 的 Redis 连接逻辑，增加降级处理。

2.  **性能优化**:
    - [ ] 将 Knowledge Retrieval 和 Coach Generation 改造为 **并行节点** (Parallel Nodes)。
    - [ ] 验证 `router.py` 在生产流量下的实际分流效果。

3.  **功能增强**:
    - [ ] 实现基于 LLM 的 **Context Summarizer**。
    - [ ] 开发 **SDR Agent** (Sales Development Representative) 的独立工作流，使其能主动发起对话。
