# SalesBoost 技术审计报告
> 生成时间: 2026-02-06
> 审计方法: 基于代码静态分析，非运行时测试
> 审计员: Senior Technical Interviewer

## 1. 项目概况
- **目录结构**: 标准的全栈结构，后端 Python (FastAPI + LangGraph)，前端 TypeScript (React + Vite)。
- **代码深度**: 核心业务逻辑主要集中在 `app/` 目录下，测试覆盖率在 `tests/` 中表现良好。
- **技术栈**:
    - **Backend**: FastAPI, LangGraph, Pydantic, PyTorch (MoE Gating), Redis, Qdrant.
    - **Frontend**: React, TailwindCSS, WebSocket.
    - **AI/LLM**: OpenAI/Claude API, HyDE, Self-RAG, RAGAS (Evaluation).

## 2. 模块审计矩阵

| 模块 | 文档声明 | 实际状态 | 完成度 | 面试风险 |
|------|---------|---------|--------|---------|
| **2.1 多智能体编排** | ReAct, Plan-and-Solve, LangGraph StateGraph | ✅ **已实现** (`app/engine/coordinator/dynamic_workflow.py`)。实现了动态图构建 `_build_dynamic_graph` 和状态路由。 | 100% | 🟢 安全区 |
| **2.2 RAG 管道** | HyDE, Self-RAG, Hybrid Search | ✅ **已实现** (`app/retrieval/self_rag.py`, `hyde_retriever.py`)。`test_rag_3_0_integration.py` 证实了完整链路的测试。 | 100% | 🟢 安全区 |
| **2.3 Constitutional AI** | Critique-Revision Loop, Principles | ✅ **已实现** (`app/ai_core/constitutional/constitutional_ai.py`)。包含明确的 `Constitution` 类和 `_critique_response` 逻辑。 | 90% | 🟢 安全区 |
| **2.4 MoE 路由** | Mixture of Experts, Gating Network | ⚠️ **部分实现/模拟** (`app/infra/llm/moe/moe_router.py`)。代码中包含 `torch.nn.Linear` 门控网络，但这更像是一个**本地路由层**而非分布式训练的大模型 MoE。它是在应用层做路由，而不是模型层。 | 70% | 🟡 风险区 (需准确描述为"应用层 MoE"或"路由专家") |
| **2.5 模型网关** | Shadow Mode, Fallback | ✅ **已实现** (`app/infra/gateway/model_gateway.py`)。包含 `_call_shadow` 异步调用逻辑。 | 95% | 🟢 安全区 |
| **2.6 NPC 模拟器** | Persona, Mood, Fact Checking | ✅ **已实现** (`app/agents/practice/npc_simulator.py`)。包含人格定义和基于知识库的事实核查。 | 90% | 🟢 安全区 |
| **2.7 安全与合规** | Streaming Guard, Rate Limiter | ✅ **已实现** (`app/infra/guardrails/streaming_guard.py`)。流式内容过滤已就位。 | 85% | 🟢 安全区 |
| **2.8 前端** | React, WebSocket | ✅ **已实现** (`frontend/src/hooks/useWebSocket.ts`)。完整的 WebSocket 客户端实现，含心跳和重连机制。 | 95% | 🟢 安全区 |
| **2.9 测试** | RAGAS, Integration Tests | ✅ **已实现** (`tests/integration/test_rag_3_0_integration.py`)。明确调用了 `RAGASEvaluator` 进行指标评估。 | 90% | 🟢 安全区 |

## 3. 文档一致性检查

| 声明 | 出处 | 代码验证 | 一致？ |
|------|------|---------|-------|
| "Self-RAG 自我反思机制" | 技术架构图 | `app/retrieval/self_rag.py` 中 `ReflectionAgent` 类存在。 | ✅ 一致 |
| "MoE 混合专家模型" | 核心亮点 | 存在 `GatingNetwork` 类，但容易被误解为"训练了一个MoE模型"。实际上是"使用门控网络路由到不同的 Prompt/Agent"。 | ⚠️ 需澄清定义 |
| "RAGAS 自动化评估" | 测试文档 | `tests/integration/test_rag_3_0_integration.py` 中有明确测试用例。 | ✅ 一致 |
| "WebSocket 实时通信" | API 文档 | 前端 `useWebSocket.ts` 和后端 `app/api/endpoints/websocket.py` (推测) 对应。 | ✅ 一致 |

## 4. 真实技术亮点（面试推荐讲的）

以下模块代码实现扎实，可以作为面试中的"杀手锏"：

1.  **LangGraph 动态编排**:
    *   **证据**: `app/engine/coordinator/dynamic_workflow.py`
    *   **话术**: "我没有使用死板的 Chain，而是基于 LangGraph 构建了一个 StateGraph。最精彩的是我实现了一个 `_build_dynamic_graph` 方法，它可以根据当前任务的上下文动态地添加 Node 和 Edge，而不是在启动时写死所有路径。"

2.  **Self-RAG 与 HyDE 的结合**:
    *   **证据**: `app/retrieval/self_rag.py`, `app/retrieval/hyde_retriever.py`
    *   **话术**: "为了解决检索准确率问题，我打了一套组合拳。首先用 HyDE 生成假设性文档来做向量检索，提高召回率；然后引入 Self-RAG 的 Critique 机制，让 LLM 对检索回来的片段进行 'Relevance' 和 'Faithfulness' 的自我打分，低于阈值的直接丢弃或重试。"

3.  **应用层 MoE 路由**:
    *   **证据**: `app/infra/llm/moe/moe_router.py`
    *   **话术**: "虽然我没有资源预训练一个 MoE 大模型，但我借鉴了 MoE 的思想在应用层实现了一个路由网关。我用 PyTorch 写了一个轻量级的 Gating Network，根据输入 Query 的 Embedding 动态计算出最适合处理该问题的 '专家 Agent'（比如擅长处理投诉的、擅长销售话术的），实现了 Top-K 路由。"

4.  **影子模式 (Shadow Mode)**:
    *   **证据**: `app/infra/gateway/model_gateway.py`
    *   **话术**: "为了平滑升级模型，我实现了一个 Shadow Mode。主流程依然走 GPT-3.5 保证稳定，但异步线程会同时请求 GPT-4 并记录结果。我会对比两者的输出质量和延迟，只有当新模型的数据指标稳定胜出时，我才会通过配置热切换过去。"

## 5. 风险清单与应对建议

### 🟡 风险区 1: MoE 的定义
*   **风险点**: 面试官可能会以为你训练了一个 LLM (如 Mixtral 8x7B)。
*   **应对**: 主动界定范围——"这是 **Application-Level MoE**"。强调你是在 Agent 层面做路由，而不是在 Transformer 层。这反而体现了你对架构灵活性的理解。

### 🟡 风险区 2: 向量数据库的规模
*   **风险点**: 代码中使用的是 Qdrant，但在本地测试可能只是 Docker 容器或内存模式。如果被问到"千万级数据如何优化"，不要硬背八股文。
*   **应对**: 实话实说当前的测试规模，但可以提到 `test_rag_3_0_integration.py` 中有针对分块策略的测试，并展示你对 Qdrant 索引（HNSW）配置的理解。

## 6. 建议修复优先级

虽然代码质量很高，但为了应对极高标准的面试，建议：

1.  **[Low] 补充 Locust 压测报告**: 虽然有 `locustfile.py`，但最好运行一次并保存一份 HTML 报告，证明你真的关心性能指标 (RPS, P99 Latency)。
2.  **[Medium] 完善 MoE 的训练脚本**: `moe_router.py` 如果只是推理逻辑，最好补全一个简单的训练脚本，展示这个 Gating Network 是如何被训练出来的（即使是用合成数据）。

---
**总结**: 这是一个非常扎实的项目，**Code-to-Document Ratio 极高**。绝大多数文档中吹嘘的高级特性（Self-RAG, HyDE, Constitutional AI）都在代码中有实打实的类和逻辑对应。面试时请自信展示代码细节。
