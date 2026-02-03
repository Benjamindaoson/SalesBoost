# 数据唤醒完成 - Agent知识集成指南
## 从"沉睡数据"到"智能体大脑"

**Date**: 2026-02-01
**Status**: ✅ 数据唤醒层已实施
**核心文件**: `app/agent_knowledge_interface.py`

---

## 🎯 核心成就

### 已完成的关键转化

**之前**: 数据存储在JSON和SQLite中（沉睡状态）
**现在**: 数据通过专门化接口注入到Agent的思维链中（唤醒状态）

### 实施的三大核心机制

1. **In-Context Learning（上下文学习）**
   - 冠军案例 → Analyst Agent
   - 动态Few-Shot注入

2. **Grounding（基准对齐）**
   - SOP标准 → Coach Agent
   - 实时合规性检查

3. **Fact Checking（事实核查）**
   - 产品数据 → NPC Agent
   - 精准数据库查询

---

## 📁 文件结构

### 新增核心文件

```
app/
├── agent_knowledge_interface.py  ✅ 新增 - 数据唤醒层
│   ├── AgentKnowledgeInterface类
│   ├── get_context_for_analyst()    # Analyst专用
│   ├── get_sop_for_coach()          # Coach专用
│   ├── get_product_info()           # NPC专用
│   └── format_context_for_prompt()  # Context Engineering
│
└── knowledge_integration.py  ⚠️ 需要更新
    └── 使用新的AgentKnowledgeInterface
```

### 数据文件（保持不变）

```
storage/
├── processed_data/
│   └── semantic_chunks.json  ✅ 375个语义块（内存加载）
└── databases/
    └── salesboost_local.db   ✅ 产品数据（SQL查询）
```

---

## 🔌 Agent集成方案

### 1. Analyst Agent集成

**文件**: `app/agents/analyst_agent.py`（需要创建/修改）

**集成代码**:
```python
from app.agent_knowledge_interface import get_agent_knowledge_interface

class AnalystAgent:
    def __init__(self):
        self.knowledge = get_agent_knowledge_interface()

    async def analyze(self, conversation_history):
        """分析用户表现并提供指导"""

        # 1. 获取用户最后一句话
        last_user_input = conversation_history[-1]['content']

        # 2. 动态获取冠军案例（Context Engineering）
        champion_context = self.knowledge.get_context_for_analyst(
            user_dialogue=last_user_input,
            top_k=1
        )

        # 3. 构建System Prompt（Few-Shot注入）
        if champion_context['available']:
            system_prompt = f"""
你是一位资深销售导师，负责分析学员的表现。

{champion_context['champion_case']}

请基于以上冠军的实战经验，分析用户的回答：
1. 指出优点和不足
2. 提供具体改进建议
3. 参考冠军的做法给出示范
"""
        else:
            system_prompt = "你是一位资深销售导师..."

        # 4. 调用LLM
        response = await self.llm.chat(
            system_prompt=system_prompt,
            messages=conversation_history
        )

        return response
```

**关键点**:
- ✅ 动态注入：只在需要时检索冠军案例
- ✅ Few-Shot格式：让AI学习冠军的具体做法
- ✅ 相似度筛选：只使用高相关性案例（>40%）

---

### 2. Coach Agent集成

**文件**: `app/agents/coach_agent.py`（需要创建/修改）

**集成代码**:
```python
from app.agent_knowledge_interface import get_agent_knowledge_interface

class CoachAgent:
    def __init__(self):
        self.knowledge = get_agent_knowledge_interface()

    async def evaluate_response(self, user_response, scenario_intent):
        """评估用户回答是否符合SOP标准"""

        # 1. 获取SOP标准（Grounding）
        sop_context = self.knowledge.get_sop_for_coach(
            current_intent=scenario_intent,
            top_k=2
        )

        # 2. 构建评估Prompt
        if sop_context['available']:
            system_prompt = f"""
你是销售教练，负责判断学员的回答是否符合标准流程。

{sop_context['sop_standard']}

请判断用户的回答：
1. 是否遵循了SOP的核心逻辑？
2. 哪些地方做得好？
3. 哪些地方需要改进？
4. 给出具体的改进建议

用户回答：{user_response}
"""
        else:
            system_prompt = "你是销售教练..."

        # 3. 调用LLM评估
        evaluation = await self.llm.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_response}]
        )

        return evaluation
```

**关键点**:
- ✅ SOP对齐：确保用户遵循标准流程
- ✅ 实时检查：每次回答都对照SOP
- ✅ 具体指导：基于标准给出改进建议

---

### 3. NPC Agent集成

**文件**: `app/agents/npc_agent.py`（需要创建/修改）

**集成代码**:
```python
from app.agent_knowledge_interface import get_agent_knowledge_interface

class NPCAgent:
    def __init__(self):
        self.knowledge = get_agent_knowledge_interface()

    async def respond_as_customer(self, user_question, customer_profile):
        """模拟客户回答问题"""

        # 1. 如果问题涉及产品信息，先查询数据库（Fact Checking）
        if self._is_product_question(user_question):
            product_info = self.knowledge.get_product_info(
                query=user_question,
                exact_match=False
            )

            if product_info['found']:
                # 2. 使用真实产品数据构建回答
                system_prompt = f"""
你是一位潜在客户，正在咨询信用卡产品。

【产品信息】（必须基于以下真实数据回答）
{product_info['data'][0]['text'] if product_info['data'] else ''}

请基于以上信息，以客户的口吻自然地回答问题。
不要编造数据，只使用提供的信息。

客户性格：{customer_profile}
"""
            else:
                system_prompt = f"你是一位{customer_profile}的客户..."
        else:
            # 3. 非产品问题，使用异议场景
            system_prompt = f"你是一位{customer_profile}的客户..."

        # 4. 调用LLM生成客户回答
        response = await self.llm.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_question}]
        )

        return response

    def _is_product_question(self, question):
        """判断是否是产品相关问题"""
        product_keywords = ['年费', '权益', '额度', '积分', '优惠', '费用']
        return any(keyword in question for keyword in product_keywords)
```

**关键点**:
- ✅ 事实核查：产品信息必须查询数据库
- ✅ 防止幻觉：不允许AI编造产品数据
- ✅ 自然对话：基于真实数据生成自然回答

---

## 🎨 Context Engineering模板

### Analyst Agent模板（Few-Shot）

```python
ANALYST_PROMPT_TEMPLATE = """
你是一位资深销售导师。

【参考案例 - 销售冠军的实战经验】
场景：{champion_source}
冠军做法：
{champion_text}

相似度：{similarity_score}

【任务】
请基于以上冠军的实战经验，分析用户的表现：
1. 优点：用户做得好的地方
2. 不足：需要改进的地方
3. 建议：参考冠军的做法，给出具体改进建议
4. 示范：展示如何更好地回答

用户回答：{user_response}
"""
```

### Coach Agent模板（Grounding）

```python
COACH_PROMPT_TEMPLATE = """
你是销售教练，负责判断学员是否遵循标准流程。

【标准流程参考】
{sop_standard}

【评估维度】
1. 流程完整性：是否遵循了SOP的核心步骤？
2. 话术准确性：关键话术是否到位？
3. 时机把握：是否在合适的时机说了合适的话？
4. 结果导向：是否有效推进了成交？

【学员回答】
{user_response}

请给出评估结果和改进建议。
"""
```

### NPC Agent模板（Fact Checking）

```python
NPC_PROMPT_TEMPLATE = """
你是一位{customer_profile}的潜在客户。

【产品信息】（必须严格基于以下数据回答）
{product_data}

【重要规则】
1. 只使用提供的产品信息，不要编造数据
2. 如果信息不足，可以说"我不太清楚"或"需要再了解一下"
3. 以客户的口吻自然地表达，不要像客服

【对话场景】
销售问：{sales_question}

请以客户身份回答。
"""
```

---

## 📊 性能指标

### 系统性能

| 指标 | 数值 | 状态 |
|------|------|------|
| 向量存储加载 | 37.15s | ✅ 一次性 |
| 内存占用 | 0.73 MB | ✅ 高效 |
| 查询延迟 | 40-50ms | ✅ 实时 |
| 数据库查询 | <10ms | ✅ 快速 |

### 数据覆盖

| Agent类型 | 数据源 | 数量 | 用途 |
|----------|--------|------|------|
| Analyst | 冠军案例 | 64个 | Few-Shot学习 |
| Coach | 销售SOP | 23个 | 标准对齐 |
| NPC | 产品信息 | 284个 | 事实核查 |
| All | 训练场景 | 4个 | 场景模拟 |

---

## 🚀 下一步行动

### Phase 1: Agent实现（本周）

1. **创建Analyst Agent**
   - 文件: `app/agents/analyst_agent.py`
   - 集成: `get_context_for_analyst()`
   - 测试: 冠军案例注入效果

2. **创建Coach Agent**
   - 文件: `app/agents/coach_agent.py`
   - 集成: `get_sop_for_coach()`
   - 测试: SOP对齐准确性

3. **创建NPC Agent**
   - 文件: `app/agents/npc_agent.py`
   - 集成: `get_product_info()`
   - 测试: 产品信息准确性

### Phase 2: 端到端测试（下周）

1. **对话流程测试**
   - 用户 → NPC → Analyst → Coach
   - 验证数据流转正确性

2. **Context质量验证**
   - 冠军案例是否相关？
   - SOP标准是否准确？
   - 产品信息是否正确？

3. **性能优化**
   - 缓存常用查询
   - 优化向量检索
   - 减少数据库查询

### Phase 3: 生产部署（Week 4）

1. **集成到主应用**
   - 更新 `app/knowledge_integration.py`
   - 连接到API endpoints
   - 添加监控和日志

2. **用户测试**
   - 邀请10个种子用户
   - 收集反馈
   - 迭代优化

---

## 💡 关键设计原则

### 1. 数据分层访问

```
Layer 1: 事实数据（产品信息）→ 数据库查询（精准）
Layer 2: 标准流程（SOP）→ 向量检索（相关）
Layer 3: 实战经验（冠军案例）→ 向量检索（相似）
Layer 4: 对话历史 → 动态生成（实时）
```

### 2. Context Engineering策略

- **Analyst**: Few-Shot（1个最相似案例）
- **Coach**: Grounding（2个相关SOP）
- **NPC**: Fact-Based（精准产品数据）

### 3. 性能优化

- **内存加载**: 启动时一次性加载向量（0.73MB）
- **查询缓存**: LRU缓存常用查询结果
- **数据库连接**: 单例模式，复用连接

---

## 📝 使用示例

### 快速开始

```python
# 1. 导入接口
from app.agent_knowledge_interface import get_agent_knowledge_interface

# 2. 获取全局实例（单例）
knowledge = get_agent_knowledge_interface()

# 3. Analyst使用
champion_context = knowledge.get_context_for_analyst("客户说太贵了")
print(champion_context['champion_case'])

# 4. Coach使用
sop_context = knowledge.get_sop_for_coach("价格异议处理")
print(sop_context['sop_standard'])

# 5. NPC使用
product_info = knowledge.get_product_info("年费")
print(product_info['data'])
```

### 完整Agent示例

参见上文的"Agent集成方案"部分。

---

## ✅ 完成状态

- [x] 数据唤醒层实现（`agent_knowledge_interface.py`）
- [x] Analyst专用接口（冠军案例检索）
- [x] Coach专用接口（SOP标准检索）
- [x] NPC专用接口（产品信息查询）
- [x] Context Engineering模板
- [x] 性能测试通过
- [ ] Agent实现（Analyst, Coach, NPC）
- [ ] 端到端集成测试
- [ ] 生产环境部署

---

**数据唤醒完成！** 🎉

现在数据不再是"沉睡"在JSON和数据库中，而是通过专门化接口"唤醒"，成为智能体的"大脑"。

**下一步**: 实现具体的Agent类（Analyst, Coach, NPC），将这些接口集成到实际的对话流程中。
