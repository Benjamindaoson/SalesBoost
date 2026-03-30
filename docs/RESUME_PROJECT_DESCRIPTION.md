# SalesBoost 项目简历描述（与代码一致版）

**Project**: SalesBoost — Enterprise-Grade Agentic Orchestration & Cognitive Training System

---

## [Orchestration: Planning & Dynamic DAG]

**从“硬编码链”向“可配置动态编排”演进**：基于 LangGraph 设计多智能体协同引擎，支持运行时配置节点（intent / knowledge / NPC / coach / compliance）与路由规则，并通过 `validate_dag` 保证图为有向无环图（DAG）。利用 **意图分类**（LLM + 关键词回退）将用户输入映射到工作流状态，经 **FSM 有限状态机**（SalesStage: OPENING → NEEDS_DISCOVERY → PRODUCT_INTRO → OBJECTION_HANDLING → CLOSING）约束状态转移与 Slot 覆盖率推进，降低长对话中的目标漂移，使业务路径在配置下可预期。

**对应实现**：`dynamic_workflow.py`（WorkflowConfig、DAG 校验）、`intent_routing.py`、`fsm.py`（SalesStage、FSMState）、`production_coordinator.py`。

---

## [Acting & Feedback: Self-Correction & Hybrid RAG]

**从“单向检索”向“带反思的混合 RAG”演进**：构建具备 **Self-RAG** 反思能力的混合检索管线。Agent 在执行工具调用时，进行 Dense + BM25 混合检索与 BGE Reranker 重排；通过 **ReflectionAgent** 对检索与生成结果做 **Relevance**（相关性）、**Faithfulness**（忠实度）、**Completeness**（完整性）量化评估。低于阈值（如 0.7）时触发 REFINE_QUERY / RETRIEVE_MORE / REGENERATE 等动作，在 **SelfRAGEngine** 中循环直至满足质量阈值，减轻 RAG 幻觉。工具参数校验失败时，通过 **execute_with_correction** 使用 ReflectionAgent 修正参数并重试。

**对应实现**：`self_rag.py`（ReflectionAgent、ReflectionDecision、SelfRAGEngine）、`hyde_retriever.py`、`vector_store.py`、`bm25_retriever.py`、`executor.py`（execute_with_correction）。

---

## [Reflection: Output Alignment & Compliance]

**从“后验审计”向“推理侧对齐与合规拦截”演进**：在输出进入生产前引入 **LLM-as-Judge** 多维度评分（task_progress、quality、satisfaction、efficiency、compliance），以及 **Compliance Agent** 的实时合规检查：基于 `COMPLIANCE_INTERCEPT_WORDS` 与风险等级进行敏感词检测，对不合规内容返回 **safe_rewrite** 建议替代话术，实现“合规截断”与安全改写，保证销售话术在商业场景下的合规性与可控性。

**对应实现**：`llm_reward_service.py`（LLM-as-Judge）、`compliance_agent.py`（check、safe_rewrite）、`quick_suggest.py`（compliance 与 safe_rewrite 注入建议）。

---

## [Infra: Hierarchical Context & Caching]

**从“单层会话存储”向“分层认知与缓存”演进**：实现 **S0–S3** 层级化上下文存储：**S0** 为 Redis 近期消息滑动窗口（LPUSH + LTRIM），**S1** 为会话摘要，**S2** 为用户档案，**S3** 为租户知识。配合 **语义缓存**（SEMANTIC_CACHE_TTL_SECONDS）与各模块 **TTL**（如会话预算、状态快照、去重键）控制生命周期，减少重复 LLM 调用与 Token 消耗，提升跨轮次上下文一致性与成本可控性。

**对应实现**：`context_manager/memory.py`（ContextMemoryStore、append_s0、write_s1/s2/s3）、`config.py`（SEMANTIC_CACHE_TTL_SECONDS）、`tool_cache.py`、`budget.py`、`snapshot.py`。

---

## 使用说明

- 可直接将上述四段按需精简后放入简历“项目描述”或“技术亮点”。
- 面试时可结合括号中的文件路径说明实现细节，避免使用代码中不存在的术语（如 “Intent-State Mapping”“Constraint Tensor”“Cognitive Decay 算法”“99.9% / 85% / 40%” 等未在实现中验证的表述）。
- 若后续有 A/B 或压测得出的准确率、成本下降等数据，可替换为“将上下文一致性提升至 X%”“单会话成本降低 Y%”等具体指标。
