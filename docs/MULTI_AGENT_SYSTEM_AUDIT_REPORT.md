# SalesBoost 多智能体系统架构审计报告

**审计日期**: 2026-01-26
**审计范围**: 智能体统一管理、模型路由、成本控制、安全规则

---

## 执行摘要

经过深入分析，SalesBoost 当前是一个**"多个模块拼在一起"的系统**，而非一个成熟的统一多智能体系统。主要问题是：

1. **双重路由系统**：存在两套独立的 LLM 路由系统，未统一
2. **死代码堆积**：存在多个未完成/未使用的模块
3. **架构分裂**：V2/V3 架构并行，配置分散

---

## 一、架构现状分析

### 1.1 入口流程

```
WebSocket 连接 (websocket.py)
    │
    ├── AGENTIC_V3_ENABLED = true
    │       └── V3Orchestrator
    │           └── 使用 model_gateway/
    │
    └── AGENTIC_V3_ENABLED = false
            └── SessionOrchestrator
                └── 使用 llm_router.py
```

### 1.2 双重路由系统问题

| 系统 | 位置 | 使用者 | 功能 |
|------|------|--------|------|
| **llm_router.py** | `app/core/` | SessionOrchestrator, cost_control.py | 简单模型映射 |
| **model_gateway/** | `app/services/` | V3Orchestrator, 40+ 文件 | 完整网关（预算、降级、指标） |

**问题**：
- 配置分散在两处（Settings 中的 `LLM_MODEL_*` vs `model_gateway/router.py`）
- 成本追踪不统一
- 无法全局监控所有 LLM 调用

---

## 二、死代码清单

### 2.1 已删除 (本次审计)

| 文件 | 原因 |
|------|------|
| `app/services/model_gateway/providers/openai.py` | 与 `openai_provider.py` 重复 |
| `app/services/model_gateway/providers/qwen.py` | 与 `qwen_provider.py` 重复 |
| `app/services/model_gateway/providers/deepseek.py` | 与 `deepseek_provider.py` 重复 |

### 2.2 需要处理的死代码

| 文件 | 状态 | 原因 |
|------|------|------|
| `app/services/orchestrator_strategy.py` | **空壳代码** | V2Strategy/V3Strategy 返回硬编码模拟数据，从未被调用 |
| `app/services/cost_control.py` | **有 Bug** | 第 276 行 `self.llm_router = get_settings()` 应为 `LLMRouter()` |
| `app/core/llm_router.py` | **冗余** | 功能被 model_gateway 覆盖，仅被旧版 V2 使用 |

---

## 三、智能体统一管理评估

### 3.1 当前状态

| 管理维度 | V2 架构 | V3 架构 | 是否统一 |
|----------|---------|---------|----------|
| **模型选择** | llm_router.py | model_gateway/router.py | ❌ 分离 |
| **成本追踪** | LangSmith (可选) | BudgetManager | ❌ 分离 |
| **预算控制** | 无 | budget.py | ❌ 仅 V3 |
| **上下文管理** | ContextBuilder | ContextBuilder | ✅ 共享 |
| **安全规则** | runtime_guard | runtime_guard | ✅ 共享 |
| **可观测性** | trace_manager | trace_manager | ✅ 共享 |

### 3.2 具体问题

#### 问题 1：模型配置分散

**V2 配置** (`app/core/config.py`):
```python
LLM_MODEL_INTENT_GATE: str = "qwen-turbo"
LLM_MODEL_NPC: str = "qwen-plus"
LLM_MODEL_COACH: str = "qwen-max"
# ...
```

**V3 配置** (`app/services/model_gateway/router.py`):
```python
self.model_configs = {
    "qwen-turbo": ModelConfig(...),
    "qwen-plus": ModelConfig(...),
    # ...
}
```

两套配置可能不一致，无法统一管理。

#### 问题 2：成本追踪分裂

- V2: 依赖 LangSmith 回调（可选）
- V3: 内置 BudgetManager + 指标埋点

无法获得全局成本视图。

---

## 四、文件结构分析

### 4.1 智能体目录

```
app/agents/
├── roles/           # V2 基础 agents
│   ├── intent_gate.py
│   ├── npc_agent.py
│   ├── coach_agent.py
│   ├── evaluator_agent.py
│   ├── rag_agent.py
│   └── compliance_agent.py
├── v3/              # V3 版本 (多数是 roles/ 的包装器)
│   ├── session_director_v3.py
│   ├── npc_generator_v3.py
│   ├── coach_generator_v3.py
│   ├── evaluator_v3.py
│   ├── retriever_v3.py
│   └── adoption_tracker_v3.py
├── coordination/    # 编排层
│   ├── orchestrator.py      # V2 入口
│   └── v3_orchestrator.py   # V3 入口
└── base.py          # Agent 基类
```

### 4.2 实际调用关系

```
V3 Agent 示例:
┌──────────────────────────┐
│ npc_generator_v3.py      │
│ ┌──────────────────────┐ │
│ │ 调用 model_gateway   │ │
│ │ 构建 prompt          │ │
│ │ 解析响应             │ │
│ └──────────────────────┘ │
│ 【不使用 roles/npc_agent】│
└──────────────────────────┘
```

V3 agents 并非简单包装 roles/ agents，而是独立实现。

---

## 五、整改建议

### 5.1 短期 (快速修复) - ✅ 已完成

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 修复 `cost_control.py` 第 276 行 bug | ✅ 已修复 |
| P1 | 删除 `orchestrator_strategy.py` | ✅ 已删除 |
| P1 | 统一环境变量到 `AGENTIC_V3_ENABLED` | ✅ 已有 |

### 5.2 中期 (架构统一) - ✅ 已完成

| 任务 | 状态 |
|------|------|
| 统一路由系统 | ✅ `llm_router.py` 改为 `model_gateway` 适配器 |
| 统一配置 | ✅ 所有配置现在从 `model_gateway/router.py` 读取 |
| 统一成本追踪 | ✅ `cost_control.py` 改为 `model_gateway.budget` 适配器 |

**架构变更摘要：**
- `app/core/llm_router.py`: 466 行 → 293 行 (适配器模式)
- `app/services/cost_control.py`: 378 行 → 167 行 (适配器模式)
- `app/services/orchestrator_strategy.py`: 已删除 (277 行死代码)

### 5.3 长期 (目标架构)

```
目标：统一智能体管理平面

                    ┌─────────────────────────┐
                    │   Unified Agent Manager │
                    │  ┌───────────────────┐  │
                    │  │ Model Router      │  │
                    │  │ Budget Manager    │  │
                    │  │ Security Rules    │  │
                    │  │ Observability     │  │
                    │  └───────────────────┘  │
                    └───────────┬─────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
   IntentGate    NPC        Coach      Evaluator     RAG
```

---

## 六、风险评估

| 风险 | 级别 | 描述 |
|------|------|------|
| 成本失控 | 高 | V2 路径无预算控制，可能超支 |
| 配置不一致 | 中 | 两套路由使用不同模型映射 |
| 维护成本 | 中 | 两套系统并行，增加开发负担 |
| 监控盲区 | 中 | V2 调用可能不在指标中 |

---

## 七、结论

### 整改前状态
SalesBoost 处于 V2 → V3 架构迁移的过渡阶段，存在**架构分裂**。

### 整改后状态 (2026-01-26)

| 维度 | 整改前 | 整改后 |
|------|--------|--------|
| 路由系统 | 两套独立系统 | ✅ 统一到 `model_gateway` |
| 配置管理 | 分散在多处 | ✅ 集中在 `model_gateway/router.py` |
| 成本追踪 | V2 无预算控制 | ✅ 统一使用 `model_gateway.budget` |
| 死代码 | 存在空壳代码 | ✅ 已清理 |

**当前架构**：
```
model_gateway (统一配置源)
    ├── llm_router.py (V2 适配器，返回 LangChain 对象)
    ├── cost_control.py (指标适配器)
    └── V3 Orchestrator (直接使用)
```

**剩余工作**：
- 当 V3 完全稳定后，可删除 V2 适配器层
- 建议将 `AGENTIC_V3_ENABLED` 默认值改为 `True`

---

*报告生成: Claude Code 审计工具*
*最后更新: 2026-01-26*
