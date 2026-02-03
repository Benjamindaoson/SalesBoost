# SalesBoost 全量架构与 PRD 合规性审计报告

**审计时间**: 2026-01-27  
**审计官**: 首席 AI 基础设施与安全审计官  
**审计范围**: 全量代码库 PRD 业务逻辑对齐 + 十维度工程质量审计

---

## 一、PRD 业务逻辑对齐审计 (Business Alignment)

### 1.1 "学-问-练-评"全闭环验证 ✅ **9/10**

**现状**:
- ✅ `app/agents/` 目录已按 `study/`, `ask/`, `practice/`, `evaluate/` 逻辑重组
- ✅ 各环节数据流转顺畅：
  - `study/retriever_v3.py`: 知识检索
  - `ask/intent_gate.py` + `ask/session_director_v3.py`: 意图识别与会话规划
  - `practice/npc_generator_v3.py` + `practice/coach_generator_v3.py`: NPC 生成与教练建议
  - `evaluate/evaluator_v3.py` + `evaluate/style_evaluator.py`: 评估与风格评分

**扣分项**:
- ⚠️ **-1分**: `evaluate/style_evaluator.py` 为新创建文件，尚未完全集成到主流程中

**建议**:
- 在 `orchestrator.py` 中集成 `StyleEvaluator`，确保博弈风格分析结果能转化为量化评分

---

### 1.2 Top 3 高频场景覆盖 ✅ **10/10**

**验证结果**:
1. ✅ **权益问答**: `app/services/quick_suggest_service.py` 实现了 `_generate_benefit_qa_suggest()`，支持权益问答建议生成
2. ✅ **客户异议处理**: `app/agents/practice/coach_generator_v3.py` 支持异议处理建议生成
3. ✅ **合规风险提示**: `app/agents/roles/compliance_agent.py` 实现了完整的合规检查与风险提示

**结论**: 三大高频场景均已完整实现

---

### 1.3 1-5 分量化评估 ✅ **8/10**

**现状**:
- ✅ `app/agents/evaluate/style_evaluator.py` 已实现五维评分（完整性、相关性、正确性、逻辑表达、合规表现）
- ✅ 评分标准严格遵循 PRD 定义：
  - 1分: 完全缺失/错误/混乱/明确违规
  - 3分: 覆盖主要环节/大体围绕问题/核心正确但有细节错误/基本有逻辑/无明显违规但不够审慎
  - 5分: 完整覆盖/高度贴合/完全准确/逻辑严密/完全合规
- ✅ 覆盖 8 大销售业务阶段（开场破冰、用户需求挖掘、产品介绍、权益介绍、异议处理、情绪安抚、跟进成交、合规表达）

**扣分项**:
- ⚠️ **-2分**: 
  1. `StyleEvaluator` 尚未与主评估流程（`EvaluatorV3`）完全集成
  2. 阶段匹配逻辑（`_match_stage()`）使用模糊匹配，可能存在误判风险

**建议**:
- 将 `StyleEvaluator.translate_style_to_scores()` 集成到 `EvaluatorV3.evaluate()` 中
- 增强阶段识别准确性，考虑使用 LLM 进行阶段判断而非纯字符串匹配

---

### 1.4 业务指标支持 ✅ **9/10**

**验证结果**:
- ✅ **对练完成率**: `app/schemas/reports.py` 中 `TrainingReport` 包含 `completion_rate` 相关字段
- ✅ **综合得分提升**: `app/schemas/reports.py` 中 `TrainingReport` 包含 `overall_score`, `score_vs_average`, `score_trend`
- ✅ **合规风险命中率**: `app/agents/roles/compliance_agent.py` 记录 `risk_flags`，可通过统计计算命中率
- ✅ **建议采纳率**: `app/schemas/reports.py` 中 `TrainingReport` 包含 `adoption_rate`, `effective_adoption_rate`

**扣分项**:
- ⚠️ **-1分**: 指标采集系统（`app/services/performance_metrics.py`）存在但未完全覆盖所有业务指标的计算逻辑

**建议**:
- 完善 `PerformanceMetricsCollector`，确保所有 PRD 要求的业务指标都能实时计算和展示

---

## 二、十维度工程质量审计 (Engineering Sovereignty)

### 2.1 交互工程 (Interaction) ✅ **9/10**

**验证结果**:
- ✅ **基于 seq_id 的 ACK 机制**: `app/api/endpoints/websocket.py` 第 35, 94-106 行实现了完整的 ACK 机制
  ```python
  self.unacked_chunks: dict[str, dict[int, dict]] = {}  # seq_id 追踪
  async def ack_chunk(self, session_id: str, seq_id: int) -> None
  ```
- ✅ **重传策略**: 第 108-132 行实现了指数退避重传（2, 4, 8, 16秒），最大重试 5 次
- ✅ **弱网环境保护**: 通过 `_retransmission_loop()` 后台任务持续监控未确认消息

**扣分项**:
- ⚠️ **-1分**: 重传逻辑中，如果客户端连续断开重连，可能导致重复消息发送（缺少去重机制）

**建议**:
- 在客户端 ACK 消息中添加消息去重标识，避免重复处理

---

### 2.2 模型工程 (Model) ✅ **10/10**

**P0 禁令检查结果**:
- ✅ **无私自调用**: 扫描 `app/` 目录（排除 `providers/`），未发现 `from openai import OpenAI` 等绕过网关的私自调用
- ✅ **合法调用位置**: 仅在以下位置使用 OpenAI SDK（均为合法）：
  - `app/services/model_gateway/providers/openai_provider.py:23`
  - `app/services/model_gateway/providers/zhipu_provider.py:21`
  - `app/services/model_gateway/providers/deepseek_provider.py:24`
- ✅ **Token 实时计费**: `app/services/model_gateway/gateway.py` 第 169-203 行强制解析所有响应的 `usage` 字段：
  ```python
  usage = result.get("usage", {})
  cost_usd = self._calculate_cost(usage, decision.model)
  ```

**结论**: 模型工程完全合规，无违规调用

---

### 2.3 推理与执行 (Execution) ✅ **9/10**

**验证结果**:
- ✅ **IntentGate 作为门卫**: `app/engine/orchestrator.py` 第 266-283 行，所有请求必须经过 `IntentGateAgent.analyze()`
- ✅ **TaskRegistry 支持多并发**: `app/engine/orchestrator.py` 第 53-76 行实现了 `TaskRegistry`，支持多并发 Slow Path 任务追踪
- ✅ **自动清理机制**: `TaskRegistry.cleanup()` 方法支持任务清理

**扣分项**:
- ⚠️ **-1分**: `TaskRegistry` 的清理逻辑需要手动调用，缺少自动超时清理机制

**建议**:
- 在 `TaskRegistry` 中添加后台任务，自动清理超时（如 5 分钟）的 Slow Path 任务

---

### 2.4 上下文工程 (Context) ✅ **10/10**

**验证结果**:
- ✅ **异步摘要由国产模型执行**: `app/services/shadow_summarizer.py` 第 130-143 行，使用 `AgentType.INTERNAL_TASK` 路由到 DeepSeek-V3
- ✅ **Layer 0 核心资产保护**: 第 23-29 行定义了 `ConversationAssetSummary`，包含：
  - `key_facts`: 关键事实
  - `pending_items`: 待办事项
  - `core_objections`: 核心异议
- ✅ **截断逻辑保护**: 摘要结果在 `_format_summary()` 中格式化，确保核心资产在上下文截断时被保护

**结论**: 上下文工程完全符合要求

---

### 2.5 记忆工程 (Memory) ⚠️ **7/10**

**验证结果**:
- ✅ **UserProfile 向量化**: `app/services/memory_service.py` 第 125-146 行实现了 `vectorize_profile()`，支持用户画像向量化
- ✅ **语义检索支持**: 第 140-142 行使用 `llm.embed()` 生成 embedding

**扣分项**:
- ⚠️ **-3分**: 
  1. 向量化逻辑仅在 `vectorize_profile()` 中实现，未发现全局的语义检索接口
  2. `UserProfile` 的向量检索功能未在代码中明确展示使用场景
  3. 缺少向量相似度检索的完整实现（如 `search_similar_profiles()` 方法）

**建议**:
- 在 `MemoryService` 中添加 `search_similar_profiles(query: str, top_k: int)` 方法
- 确保用户画像检索使用向量相似度而非字符串匹配

---

### 2.6 知识工程 (Knowledge) ⚠️ **8/10**

**验证结果**:
- ✅ **来源展示支持**: `app/schemas/agent_outputs.py` 第 115 行，`RAGItem` 包含 `source_citations: List[str]` 字段
- ✅ **可追溯性**: `app/agents/study/retriever_v3.py` 第 118-124 行，检索结果包含 `source` 和 `source_type` 字段

**扣分项**:
- ⚠️ **-2分**: 
  1. 未发现明确的 RAG 准确率验证机制（如 `≥95%` 的标准验证）
  2. 来源展示在部分场景下可能为空（第 120 行：`source=", ".join(item.source_citations) if item.source_citations else "unknown"`）

**建议**:
- 在 `RetrieverV3` 或 `KnowledgeEngine` 中添加准确率验证逻辑
- 确保所有 RAG 输出都包含有效的来源信息，禁止返回 "unknown"

---

### 2.7 集成工程 (Integration) ✅ **10/10**

**验证结果**:
- ✅ **Whisper 转写收口**: `app/services/llm_service.py` 第 239-265 行，`transcribe()` 方法通过统一网关调用
- ✅ **全局预算管理**: 第 252-256 行，转写任务使用 `_build_context()` 构建路由上下文，接受预算管理
- ✅ **流式任务统一**: 所有流式任务（chat_stream, transcribe）均通过 `ModelGateway` 统一管理

**结论**: 集成工程完全符合要求

---

### 2.8 可观测性 (Observability) ✅ **10/10**

**验证结果**:
- ✅ **异步化写入**: `app/services/observability/trace_manager.py` 第 30-51 行实现了异步持久化：
  ```python
  self._queue = asyncio.Queue()
  self._worker_task = loop.create_task(self._persistence_worker())
  ```
- ✅ **Queue + Worker 模式**: 第 41-51 行，`_persistence_worker()` 从队列中异步处理 trace 写入
- ✅ **无同步磁盘 IO**: 第 47 行使用 `asyncio.to_thread()` 将同步 IO 操作放到线程池，不阻塞主线程

**结论**: 可观测性工程完全符合要求，无同步 IO 阻塞风险

---

### 2.9 安全工程 (Security) ⚠️ **7/10**

**验证结果**:
- ✅ **RuntimeGuard 实现**: `app/security/runtime_guard.py` 实现了输入/输出安全检查
- ✅ **Look-ahead Buffer**: `app/engine/orchestrator.py` 第 326-337 行实现了 20 token 的 look-ahead buffer

**扣分项**:
- ⚠️ **-3分**: 
  1. **关键问题**: Look-ahead Buffer 仅缓冲 20 个 token，但合规扫描在流式输出**之后**进行（第 346-352 行），而非在推送前端**之前**100% 扫描
  2. 第 329-331 行：buffer 达到 20 个 token 时立即 yield，未经过合规扫描
  3. 第 346 行的 `check_output()` 在流式输出完成后才执行，存在合规风险

**严重性**: 🔴 **Critical** - 流式输出可能在合规扫描完成前就推送到前端

**建议**:
- **立即修复**: 在 `_execute_fast_path_stream()` 中，确保每个 token 在 yield 前都经过合规扫描
- 实现滑动窗口合规检查：每累积 20 个 token 时，先进行合规扫描，通过后再 yield
- 如果检测到违规，立即停止流式输出并触发安全事件

---

### 2.10 治理工程 (Governance) ✅ **9/10**

**验证结果**:
- ✅ **内部治理任务路由**: `app/services/model_gateway/router.py` 第 248 行，`AgentType.INTERNAL_TASK` 默认路由到 `deepseek-chat`（国产模型）
- ✅ **意图判定路由**: 第 236 行，`AgentType.INTENT_GATE` 默认使用 `qwen-turbo`（国产模型）
- ✅ **摘要任务路由**: `app/services/shadow_summarizer.py` 第 136 行，使用 `AgentType.INTERNAL_TASK`，自动路由到国产模型

**扣分项**:
- ⚠️ **-1分**: 评分任务（`AgentType.EVALUATOR`）默认使用 `glm-4`（第 245 行），虽然也是国产模型，但成本较高，可考虑降级到 `qwen-turbo` 或 `deepseek-chat`

**建议**:
- 评估 `EVALUATOR` 使用 `glm-4` 的必要性，如无特殊要求，建议降级到 `deepseek-chat` 以降低成本

---

## 三、合规性评分汇总

| 维度 | 评分 | 状态 |
|------|------|------|
| PRD 业务逻辑对齐 | 9.0/10 | ✅ 优秀 |
| 交互工程 | 9.0/10 | ✅ 优秀 |
| 模型工程 | 10.0/10 | ✅ 完美 |
| 推理与执行 | 9.0/10 | ✅ 优秀 |
| 上下文工程 | 10.0/10 | ✅ 完美 |
| 记忆工程 | 7.0/10 | ⚠️ 需改进 |
| 知识工程 | 8.0/10 | ✅ 良好 |
| 集成工程 | 10.0/10 | ✅ 完美 |
| 可观测性 | 10.0/10 | ✅ 完美 |
| 安全工程 | 7.0/10 | 🔴 **Critical** |
| 治理工程 | 9.0/10 | ✅ 优秀 |

**总体评分**: **8.9/10** (优秀，但存在 Critical 安全风险)

---

## 四、漏洞/违规列表

### 🔴 Critical (必须立即修复)

1. **安全工程 - 流式输出合规扫描时机错误**
   - **位置**: `app/engine/orchestrator.py` 第 326-352 行
   - **问题**: Look-ahead Buffer 中的 token 在合规扫描**之前**就推送到前端
   - **风险**: 违规内容可能在扫描完成前就暴露给用户
   - **修复方案**: 见下方重构建议

### ⚠️ Warning (建议修复)

1. **StyleEvaluator 未完全集成**
   - **位置**: `app/agents/evaluate/style_evaluator.py`
   - **问题**: 新创建的评估代理尚未集成到主流程
   - **影响**: 博弈风格分析无法转化为量化评分

2. **UserProfile 语义检索功能不完整**
   - **位置**: `app/services/memory_service.py`
   - **问题**: 缺少 `search_similar_profiles()` 等语义检索接口
   - **影响**: 用户画像检索可能降级为字符串匹配

3. **RAG 准确率验证缺失**
   - **位置**: `app/agents/study/retriever_v3.py`
   - **问题**: 未发现明确的 `≥95%` 准确率验证机制
   - **影响**: 无法保证 RAG 输出质量

4. **TaskRegistry 缺少自动清理**
   - **位置**: `app/engine/orchestrator.py` 第 53-76 行
   - **问题**: 需要手动调用 `cleanup()`，缺少超时自动清理
   - **影响**: 可能导致内存泄漏

---

## 五、架构退化风险

### 5.1 性能瓶颈风险

1. **同步 IO 风险** ✅ **已规避**
   - `TraceManager` 已完全异步化，无同步磁盘 IO 阻塞风险

2. **状态机断层风险** ⚠️ **低风险**
   - `FSMState` 管理良好，但需要确保状态恢复逻辑的完整性

### 5.2 逻辑混乱风险

1. **评估流程分散** ⚠️ **中风险**
   - `EvaluatorV3` 和 `StyleEvaluator` 功能重叠，需要统一评估流程
   - 建议：将 `StyleEvaluator` 作为 `EvaluatorV3` 的组件，而非独立服务

2. **路由策略不一致** ✅ **低风险**
   - 路由逻辑集中在 `ModelRouter`，策略一致性好

---

## 六、重构建议

### 6.1 🔴 Critical: 修复流式输出合规扫描

**文件**: `app/engine/orchestrator.py`

**当前代码** (第 326-352 行):
```python
look_ahead_buffer = []
async for chunk in self.npc_generator.generate_stream(...):
    if chunk["type"] == "token":
        content = chunk["content"]
        npc_text_accumulator.append(content)
        look_ahead_buffer.append(content)
        
        # Buffer size 20 for security scanning
        if len(look_ahead_buffer) >= 20:
            to_yield = look_ahead_buffer.pop(0)  # ❌ 未扫描就 yield
            yield {"type": "token", "content": to_yield}

# 5. Output Security Check (在流式输出完成后)
out_action, modified_text, out_event = runtime_guard.check_output(npc_text)
```

**修复方案**:
```python
look_ahead_buffer = []
async for chunk in self.npc_generator.generate_stream(...):
    if chunk["type"] == "token":
        content = chunk["content"]
        npc_text_accumulator.append(content)
        look_ahead_buffer.append(content)
        
        # Buffer size 20 for security scanning
        if len(look_ahead_buffer) >= 20:
            # ✅ 先扫描，再 yield
            buffer_text = "".join(look_ahead_buffer)
            out_action, scanned_text, out_event = runtime_guard.check_output(buffer_text)
            
            if out_action == SecurityAction.BLOCK:
                # 立即停止流式输出
                trace_manager.record_security_event(fast_trace_id, out_event)
                yield {"type": "error", "message": "Content blocked by security check"}
                break
            
            # 只 yield 第一个 token（已通过扫描）
            to_yield = look_ahead_buffer.pop(0)
            yield {"type": "token", "content": to_yield}

# Flush remaining buffer (也需要扫描)
if look_ahead_buffer:
    buffer_text = "".join(look_ahead_buffer)
    out_action, scanned_text, out_event = runtime_guard.check_output(buffer_text)
    if out_action != SecurityAction.BLOCK:
        for token in look_ahead_buffer:
            yield {"type": "token", "content": token}
```

### 6.2 集成 StyleEvaluator

**文件**: `app/agents/evaluate/evaluator_v3.py`

**建议修改**:
```python
from app.agents.evaluate.style_evaluator import StyleEvaluator

class EvaluatorV3:
    def __init__(self, ...):
        ...
        self.style_evaluator = StyleEvaluator()
    
    async def evaluate(self, ...) -> Evaluation:
        # 1. 执行基础评估
        evaluator_output, strategy_analysis = await self.evaluator_agent.evaluate(...)
        
        # 2. 如果存在博弈风格分析，转化为量化评分
        if style_analysis:  # 需要从上下文获取
            style_scores = await self.style_evaluator.translate_style_to_scores(
                style_analysis=style_analysis,
                conversation_history=conversation_history,
                session_id=session_id,
                turn_number=turn_number,
            )
            # 融合 style_scores 到最终评估结果
        
        # 3. 转换为 Evaluation
        ...
```

### 6.3 完善 UserProfile 语义检索

**文件**: `app/services/memory_service.py`

**建议添加**:
```python
async def search_similar_profiles(
    self,
    query: str,
    top_k: int = 5,
    tenant_id: str = "public",
) -> List[UserProfile]:
    """基于向量相似度搜索相似用户画像"""
    # 1. 生成查询向量
    query_embedding = await self.llm_service.embed([query])
    if not query_embedding:
        return []
    
    # 2. 从数据库加载所有用户画像
    profiles = await self._load_all_profiles(tenant_id)
    
    # 3. 计算余弦相似度
    similarities = []
    for profile in profiles:
        if not profile.embedding:
            continue
        similarity = self._cosine_similarity(query_embedding[0], profile.embedding)
        similarities.append((profile, similarity))
    
    # 4. 排序并返回 top_k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in similarities[:top_k]]
```

### 6.4 添加 RAG 准确率验证

**文件**: `app/agents/study/retriever_v3.py`

**建议添加**:
```python
async def retrieve(self, ...) -> EvidencePack:
    ...
    # 验证检索准确率
    if retrieval_mode == "graphrag":
        # GraphRAG 准确率要求 ≥95%
        min_confidence = 0.95
        evidence_items = [e for e in evidence_items if e.confidence >= min_confidence]
        
        if len(evidence_items) < top_k * 0.8:  # 如果准确率不足，降级到向量检索
            logger.warning("GraphRAG accuracy below threshold, falling back to vector retrieval")
            retrieval_mode = "lightweight"
            # 重新执行向量检索
            ...
    
    # 确保所有结果都有来源
    for item in evidence_items:
        if not item.source or item.source == "unknown":
            logger.warning(f"Evidence item missing source: {item.content[:50]}")
            item.source = "unknown_source"  # 至少标记为未知来源，而非空
    
    return EvidencePack(...)
```

### 6.5 TaskRegistry 自动清理

**文件**: `app/engine/orchestrator.py`

**建议修改**:
```python
class TaskRegistry:
    def __init__(self):
        self._tasks: Dict[int, asyncio.Task] = {}
        self._abort_signals: Dict[int, asyncio.Event] = {}
        self._task_timestamps: Dict[int, float] = {}  # 添加时间戳
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_loop()
    
    def _start_cleanup_loop(self):
        """启动自动清理循环"""
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._auto_cleanup_loop())
        except RuntimeError:
            pass
    
    async def _auto_cleanup_loop(self):
        """自动清理超时任务（每 30 秒检查一次）"""
        while True:
            await asyncio.sleep(30)
            now = time.time()
            timeout_seconds = 300  # 5 分钟超时
            
            to_cleanup = []
            for turn_number, timestamp in self._task_timestamps.items():
                if now - timestamp > timeout_seconds:
                    to_cleanup.append(turn_number)
            
            for turn_number in to_cleanup:
                logger.info(f"Auto-cleaning timeout task: turn {turn_number}")
                self.cleanup(turn_number)
    
    def add_task(self, turn_number: int, task: asyncio.Task, abort_signal: asyncio.Event):
        self._tasks[turn_number] = task
        self._abort_signals[turn_number] = abort_signal
        self._task_timestamps[turn_number] = time.time()  # 记录时间戳
```

---

## 七、总结

### 7.1 亮点

1. ✅ **模型工程完美合规**: 无任何私自调用，所有 LLM 调用均通过统一网关
2. ✅ **可观测性优秀**: TraceManager 完全异步化，无同步 IO 阻塞
3. ✅ **集成工程完善**: 所有流式任务统一收口，接受全局预算管理
4. ✅ **上下文工程优秀**: ShadowSummarizer 正确使用国产模型，Layer 0 资产保护完善

### 7.2 关键风险

1. 🔴 **Critical**: 流式输出合规扫描时机错误，存在安全风险
2. ⚠️ **Warning**: StyleEvaluator 未完全集成，功能未闭环
3. ⚠️ **Warning**: UserProfile 语义检索功能不完整

### 7.3 改进优先级

1. **P0 (立即修复)**: 流式输出合规扫描修复
2. **P1 (本周内)**: StyleEvaluator 集成、UserProfile 语义检索完善
3. **P2 (本月内)**: RAG 准确率验证、TaskRegistry 自动清理

---

**审计结论**: SalesBoost 项目整体架构优秀（8.9/10），但在安全工程方面存在 Critical 风险，需要立即修复。其他问题多为功能完善和优化，不影响核心功能。

**建议**: 优先修复流式输出合规扫描问题，确保系统安全性。随后逐步完善其他功能，提升整体工程质量至 10/10。
