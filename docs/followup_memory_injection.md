# 长线销售追踪（Task Follow-up）模块实现文档

## 概述

本模块实现了"长线销售追踪"功能，通过两个核心提示词驱动：
1. **NPC 记忆注入提示词** - 让客户"记得"上次聊了什么
2. **教练策略预演提示词** - 告诉销售针对上次的遗留问题该怎么出招

## 核心组件

### 1. 提示词文件（使用 Jinja2 模板引擎）

#### NPC 记忆唤醒提示词
- **文件路径**: `app/core/prompts/npc_memory_injection_prompt.md`
- **功能**: 将 Shadow Summarizer 提取的 `pending_items` 和 `core_objections` 转化为 NPC 的初始情绪和开场白
- **模板变量**:
  - `scene_description`: 场景描述
  - `customer_profile`: 客户画像（包含姓名、行业、性格等）
  - `initial_needs`: 原始需求
  - `key_facts`: 核心事实列表
  - `core_objections`: 遗留异议列表
  - `pending_items`: 待办任务列表
  - `customer_sentiment`: 历史情绪 (Positive/Negative/Neutral)
- **关键特性**:
  - 记忆触发现场：在前 3 轮内主动提及待办任务或遗留异议
  - 阻力阈值调节：针对遗留异议，如果销售未给出更具说服力的话术，态度将持续保持冷淡
  - 意图锚定：决策逻辑保持一致，严禁推翻上次已达成的共识

#### 教练跟进提示词
- **文件路径**: `app/core/prompts/coach_strategy_brief_prompt.md`
- **功能**: 在会话开始前生成战术简报
- **模板变量**:
  - `learner_weaknesses`: 学员历史弱项
  - `scores`: 基于 PRD 5 维度评估得分
  - `core_objections`: 客户遗留卡点列表
  - `pending_items`: 本次突破目标列表
  - `weakness_dimension`: 短板维度
- **输出内容**:
  1. 战术引导：针对客户遗留卡点，提示使用"权益价值对冲法"
  2. 短板纠偏：识别学员历史表现不佳的维度，给出预防性建议
  3. 行动指引：提示本轮对话的通关标志

#### 博弈风格捕捉提示词（进阶功能）
- **文件路径**: `app/core/prompts/style_pattern_summarizer_prompt.md`
- **功能**: 分析销售在处理复杂异议时的"博弈风格"
- **评估维度**:
  - 亲和力 (Rapport): 顾问式沟通 vs 机械回答
  - 推进感 (Momentum): 成交推进意识强度
  - 合规稳健度 (Compliance): 话术审慎程度
  - 博弈类型: 强力说服型 / 利益引导型 / 情感链接型

### 2. 提示词渲染服务

**文件**: `app/services/prompt_renderer.py`

使用 Jinja2 模板引擎进行变量填充，提供以下方法：

- `render_npc_memory_injection()`: 渲染 NPC 记忆注入提示词
- `render_coach_strategy_brief()`: 渲染教练策略预演提示词
- `render()`: 通用模板渲染方法（支持自定义模板）

### 2. Shadow Summarizer 增强

**文件**: `app/services/shadow_summarizer.py`

新增方法：
```python
def get_latest_summary(self, session_id: str) -> Optional[ConversationAssetSummary]:
    """
    获取会话的最新摘要（用于记忆注入）。
    返回最近生成的 ConversationAssetSummary，不依赖 history_text。
    """
```

### 3. NPC Agent 记忆注入

**文件**: `app/agents/roles/credit_card_prospect_agent.py`

修改内容：
- 在 `__init__` 中添加 `memory_summary` 参数
- 修改 `_system_prompt()` 方法，当存在记忆摘要时使用记忆注入提示词模板

### 4. NPC Generator V3 集成

**文件**: `app/agents/practice/npc_generator_v3.py`

修改内容：
- 在 `__init__` 中添加 `memory_summary` 参数
- 将记忆摘要传递给 `CreditCardProspectAgent`

### 5. Coach Agent 策略预演

**文件**: `app/agents/practice/coach_agent.py`

新增方法：
```python
async def generate_strategy_brief(
    self,
    memory_summary: ConversationAssetSummary,
    learner_weaknesses: Optional[str] = None,
    llm_context: Optional["LLMCallContext"] = None,
) -> str:
    """
    生成策略预演简报（战前布防）
    """
```

### 6. Coordinator 记忆装载

**文件**: `app/engine/coordinator.py`

修改内容：
- 添加 `memory_summary` 属性
- 在 `initialize_session()` 中调用 `_load_memory_summary()` 加载上次对话摘要
- 新增 `_load_memory_summary()` 方法从 Shadow Summarizer 获取最新摘要

### 7. Orchestrator 集成

**文件**: `app/engine/orchestrator.py`

修改内容：
- 在 `initialize_session()` 中，如果存在记忆摘要，重新创建 NPC Generator 以注入记忆

## 工作流程

### 会话初始化流程

1. **Coordinator.initialize_session()** 被调用
2. **Coordinator._load_memory_summary()** 从 Shadow Summarizer 获取最新摘要
3. 如果存在摘要，**Orchestrator** 重新创建 NPC Generator 并注入记忆
4. NPC Agent 的 system prompt 包含记忆注入提示词

### NPC 生成流程

1. NPC Generator 调用 CreditCardProspectAgent
2. CreditCardProspectAgent 检查是否有 `memory_summary`
3. 如果有，使用记忆注入提示词模板生成 system prompt
4. NPC 在前 3 轮内主动提及待办事项或核心异议

### 教练策略预演流程

1. 在会话开始前（或需要时），调用 `CoachAgent.generate_strategy_brief()`
2. 传入 `memory_summary` 和 `learner_weaknesses`
3. 使用策略预演提示词模板生成简报
4. 返回简洁的教练提示格式文本

## 使用示例

### 在会话初始化时自动加载记忆

```python
# Coordinator 会自动在 initialize_session 时加载记忆
coordinator.initialize_session(session_id, user_id, fsm_state)

# 检查是否加载了记忆
if coordinator.memory_summary:
    print(f"已加载记忆：{len(coordinator.memory_summary.pending_items)} 个待办事项")
```

### 生成策略预演简报

```python
from app.agents.practice.coach_agent import CoachAgent
from app.core.llm_context import LLMCallContext

coach_agent = CoachAgent()
llm_context = LLMCallContext(session_id=session_id, turn_number=0)

# 获取记忆摘要
memory_summary = coordinator.memory_summary

# 生成策略预演简报
brief = await coach_agent.generate_strategy_brief(
    memory_summary=memory_summary,
    learner_weaknesses="处理异议时缺乏耐心，容易陷入价格争论",
    scores="异议处理: 0.4, 价值重塑: 0.6, 成交推进: 0.5",
    weakness_dimension="异议处理",
    llm_context=llm_context
)

print(brief)
# 输出示例：
# ## 策略预演简报
# 1. **首要任务**: 优先处理客户遗留的【年费减免政策确认】
# 2. **话术样板**: 针对客户的核心异议，使用"权益覆盖成本"的逻辑进行回应。
# 3. **风险预警**: 避免重复上次对话中的错误，保持专业和耐心。
```

### 使用提示词渲染服务

```python
from app.services.prompt_renderer import get_prompt_renderer

renderer = get_prompt_renderer()

# 渲染 NPC 记忆注入提示词
npc_prompt = renderer.render_npc_memory_injection(
    scene_description="信用卡销售场景 - 高端客户年费异议处理",
    customer_profile="王先生，经常出差的商务人士；性格：对价格敏感、理性决策",
    initial_needs="经常出差但没有机场贵宾厅权益",
    key_facts=["月均消费约2万元", "有商旅习惯", "已持有3张信用卡"],
    core_objections=["年费太贵", "不信任自动分期"],
    pending_items=["查询高尔夫权益场馆", "对比他行额度"],
    customer_sentiment="Negative",
)

# 渲染教练策略预演提示词
coach_prompt = renderer.render_coach_strategy_brief(
    learner_weaknesses="处理异议时缺乏耐心，容易陷入价格争论",
    scores="异议处理: 0.4, 价值重塑: 0.6",
    core_objections=["年费太贵", "不信任自动分期"],
    pending_items=["查询高尔夫权益场馆", "对比他行额度"],
    weakness_dimension="异议处理",
)
```

## 数据流

```
Shadow Summarizer (异步摘要)
    ↓
ConversationAssetSummary (pending_items, core_objections, customer_sentiment)
    ↓
Coordinator._load_memory_summary()
    ↓
Coordinator.memory_summary
    ↓
┌─────────────────────────┬──────────────────────────┐
│                         │                          │
NPC Generator             │  Coach Agent             │
    ↓                     │      ↓                   │
CreditCardProspectAgent   │  generate_strategy_brief │
    ↓                     │      ↓                   │
记忆注入提示词            │  策略预演简报            │
    ↓                     │      ↓                   │
NPC 回复（包含记忆）      │  教练提示（战前布防）    │
```

## 注意事项

1. **记忆摘要的获取时机**: 记忆摘要是异步生成的，只有在 Shadow Summarizer 完成摘要后才会在下次会话中可用。

2. **会话 ID 的连续性**: 确保使用相同的 `session_id` 或相关的会话标识，以便 Shadow Summarizer 能够正确关联摘要。

3. **记忆摘要的时效性**: 当前实现使用内存缓存，如果服务重启，缓存会丢失。生产环境建议持久化到数据库。

4. **策略预演的成本**: `generate_strategy_brief()` 会调用 LLM，注意控制调用频率和成本。

## 技术实现细节

### Jinja2 模板引擎

系统使用 Jinja2 进行提示词模板渲染，具有以下优势：

1. **类型安全**: 支持列表、字典等复杂数据结构
2. **错误处理**: 模板文件不存在时自动使用兜底内容
3. **可扩展性**: 易于添加新的模板变量和逻辑

### 模板变量填充流程

```
Shadow Summarizer (异步摘要)
    ↓
ConversationAssetSummary
    ↓
PromptRenderer.render_npc_memory_injection()
    ↓
Jinja2 Template Engine
    ↓
填充后的提示词文本
    ↓
NPC Agent / Coach Agent
```

### 场景描述和客户画像的获取

- **场景描述**: 从 `ScenarioConfig.scenario_background` 或 `ScenarioConfig.description` 获取
- **客户画像**: 从 `CustomerPersona` 的多个字段组合构建：
  - `name` + `occupation`: 基本信息
  - `personality_traits`: 性格特征
  - `buying_motivation`: 购买动机
  - `main_concerns`: 主要顾虑（作为原始需求）

## 未来优化方向

1. **博弈风格捕捉**: 在 Shadow Summarizer 中加入"博弈风格捕捉"，使用 `style_pattern_summarizer_prompt.md` 提示词分析销售风格，并将结果存入 `UserProfile` 的向量空间。

2. **持久化存储**: 将记忆摘要持久化到数据库，支持跨服务重启的记忆恢复。

3. **记忆衰减机制**: 实现记忆衰减机制，较旧的记忆摘要权重降低。

4. **多会话记忆关联**: 支持同一客户在不同会话间的记忆关联。

5. **动态模板加载**: 支持从数据库或配置文件动态加载提示词模板，无需重启服务即可更新。
