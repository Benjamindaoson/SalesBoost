# Findings: SalesBoost 项目深度分析报告

## 一、项目定性

**是多智能体系统 (Multi-Agent System)**，基于 **LangGraph** 框架构建，属于企业级 AI 销售赋能平台。

---

## 二、核心框架与技术栈

| 层次 | 技术 |
|------|------|
| AI 编排框架 | **LangGraph** (StateGraph + END nodes) |
| LLM 接入 | OpenAI API + Anthropic Claude API |
| 后端 Web | FastAPI 0.109+ (async) |
| 数据库 | PostgreSQL (asyncpg) + SQLAlchemy 2.0 async |
| 向量数据库 | **Qdrant** |
| 缓存/消息队列 | Redis + Celery |
| 向量模型 | sentence-transformers (BAAI/BGE-M3) |
| 混合检索 | BM25 (rank-bm25) + Dense + Reranker |
| 前端 | React 18 + TypeScript + TailwindCSS |
| 可观测性 | OpenTelemetry + Prometheus + Sentry |
| 迁移 | Alembic |
| NLP | jieba (中文分词) + tiktoken |

---

## 三、多智能体架构详解

### Agent 角色列表

| Agent | 路径 | 职责 |
|-------|------|------|
| SDRAgentEnhanced | agents/autonomous/ | AI 销售代表，AI 驱动决策 + PPO RL + 三层记忆 |
| CoachAgent | agents/ask/ | 实时销售教练，提供改进建议 |
| ComplianceAgent | agents/roles/ | 合规检查，拦截违规话术 |
| NPC Simulator | agents/practice/ | 模拟客户，支持多种性格类型 |
| UserSimulator | agents/simulation/ | 用户行为仿真 |
| EvaluateAgent | agents/evaluate/ | 多维度会话评分与报告生成 |
| MemoryAgent | agents/memory/ | 三层记忆网络（情节/语义/工作记忆）|

### 编排机制 (LangGraph)

```
ProductionCoordinator (Facade)
    └─→ DynamicWorkflowCoordinator (LangGraph StateGraph)
            ├─ 节点: NPC响应 / Coach分析 / Compliance检查
            ├─ Contextual Bandit 路由决策
            ├─ ReasoningEngine 推理
            └─ HumanInLoopCoordinator (人工审核工作流)
```

---

## 四、技术亮点（10大核心亮点）

### 1. LangGraph 动态工作流引擎
- 使用 `StateGraph + END` 构建可配置的 Agent 执行图
- 支持 Feature Flag 动态切换引擎（DynamicWorkflow vs LangGraph）
- Facade 模式解耦业务逻辑与底层引擎

### 2. Contextual Bandit 智能路由
- `SimpleContextualBandit` + `RedisContextualBandit`
- 基于上下文的 Agent 路由 A/B 测试
- 支持分布式 Redis 场景下的水平扩展

### 3. Enhanced GraphRAG（多跳知识推理）
- 基于 LLM 的实体和关系抽取（替代关键词匹配）
- 知识图谱多跳推理（最多 3 跳）
- 路径发现：从对话 → 知识图谱 → 销售洞察
- 混合检索：BM25 + Dense Embedding + Reranker

### 4. 三层记忆架构
- 情节记忆 (Episodic): 具体交互事件
- 语义记忆 (Semantic): 抽象知识
- 工作记忆 (Working): 短期活跃信息
- 向量相似度检索 + 重要性评估 + 遗忘机制

### 5. 销售对话 FSM（有限状态机）
- 7 个状态：Opening → Discovery → Pitch → Objection → Closing → Completed/Failed
- 事件驱动状态转移（13 种 Trigger）
- 置信度感知的状态转换记录

### 6. RLAIF 数据飞轮
- 自动收集高质量对话样本
- 用 Claude 3.5 打标（AI Feedback）
- 生成训练数据 → 微调轻量模型
- A/B 测试支持 + 性能追踪

### 7. Data Flywheel（业务闭环）
- 从 Closed-Won 成交单提取获胜模式
- 方法论维度（MEDDPICC）关联分析
- 优秀话术自动反哺 RAG 知识库
- 形成「赢单 → 提炼 → 改进 → 再赢单」正向循环

### 8. Live Assist 三阶段决策链
```
客户话语 → Stage 1: 意图识别 → Stage 2: 阶段推断(LLM+FSM混合)
         → Stage 3: 策略生成(MEDDPICC缺口+个人弱项注入)
```
- 单次 LLM 调用完成三阶段（<2s 延迟）
- 可解释性：Chain-of-thought rationale 展示给销售

### 9. Constitutional AI 价值对齐
- 定义销售伦理宪法（5 大原则：诚实/尊重/准确/同理/合规）
- 自我批评和修正循环（Self-Critique Loop）
- Compliance Agent 实时拦截违规话术

### 11. Prompt 配置文件化（业务与引擎解耦）
- Constitutional AI 原则、Live Assist system prompt、FSM 阶段定义均提取为带 frontmatter 的 Markdown 配置文件
- 由 `prompt_registry` 统一管理，支持版本号、SHA256 hash、变量替换（`.format()`）
- `core_startup.py` 启动时自动扫描 `core/prompts/` 目录加载所有配置，零改动即生效
- 运营人员可直接修改 `.md` 文件调整 AI 行为，无需改代码或重新部署

### 10. 生产级基础设施
- Model Gateway：统一 LLM 路由 + Shadow Mode（异步镜像测试）
- Redis 分布式信号量（水平扩展并发控制）
- OpenTelemetry 全链路追踪 + Prometheus 指标 + Sentry 异常
- 多租户中间件 (TenantMiddleware)
- 三大销售方法论引擎：MEDDPICC / SPIN / Challenger

---

## 五、亮点总结

这是一个**完整的 AI-Native 企业级系统**，而非玩具项目：
- 从 Agent 编排（LangGraph）到向量检索（Qdrant/GraphRAG）
- 从强化学习（PPO/RLAIF）到 Constitutional AI
- 从业务闭环（Data Flywheel）到生产监控（OTel/Prometheus）
- 全栈实现（Python FastAPI + React TypeScript）
- 多智能体协作覆盖销售全流程

SalesBoost 项目深度分析报告
一、这是多智能体系统吗？
是的，是一个完整的多智能体系统（Multi-Agent System）。

基于 LangGraph 框架（LangChain 生态）构建，采用 StateGraph 有向图编排多个专职 Agent 协同工作。

二、核心技术架构

ProductionCoordinator (Facade 门面层)
    └─→ DynamicWorkflowCoordinator (LangGraph StateGraph)
            ├─ Contextual Bandit 智能路由
            ├─ ReasoningEngine 推理引擎
            ├─ HumanInLoopCoordinator 人工审核
            └─ 各专职 Agent 节点
Agent 角色分工
Agent	职责
SDRAgentEnhanced	AI销售代表：LLM决策 + PPO强化学习 + 三层记忆
CoachAgent	实时销售教练，逐轮给出改进建议
ComplianceAgent	合规审查，实时拦截违规话术
NPC Simulator	模拟客户（多性格类型）
EvaluateAgent	多维度会话评分与报告生成
三、十大技术亮点
1. LangGraph 动态工作流（核心框架）
StateGraph + END 构建可配置执行图
Feature Flag 驱动动态引擎切换
Facade 模式解耦，向后兼容所有 Coordinator
2. Contextual Bandit 智能路由
SimpleContextualBandit + RedisContextualBandit（分布式）
上下文感知的 Agent 路由，内置 A/B 测试
Redis 分布式信号量支持水平扩展
3. Enhanced GraphRAG（多跳知识推理）
LLM 驱动的实体/关系抽取（非关键词匹配）
知识图谱最多 3 跳推理
混合检索：BM25 + Dense Embedding (BGE-M3) + Reranker
4. 三层记忆架构
情节记忆 / 语义记忆 / 工作记忆
向量相似度检索 + 重要性衰减 + 遗忘机制
5. 销售对话 FSM（有限状态机）
7 状态：Opening→Discovery→Pitch→Objection→Closing→Done/Failed
13 种事件触发器，置信度感知的转移记录
6. RLAIF 数据飞轮（AI自我改进）
自动收集高质量对话 → Claude 3.5 打标签（AI Feedback）
生成训练数据 → 微调轻量模型 → 持续迭代
7. Business Data Flywheel（业务闭环）
从 Closed-Won 成交单提取「获胜模式」
优秀话术自动反哺 RAG 知识库
「赢单 → 提炼 → 改进 → 再赢单」正向循环
8. Live Assist 三阶段决策链

客户话语 → 意图识别 → 阶段推断(LLM+FSM混合) → 策略生成
单次 LLM 调用完成三阶段（目标 <2s 延迟）
Chain-of-thought 可解释性，rationale 实时展示
9. Constitutional AI 价值对齐
定义销售伦理宪法（诚实/尊重/准确/同理/合规 5大原则）
Self-Critique 自我批评修正循环
10. 生产级基础设施
Model Gateway：多 LLM 路由 + Shadow Mode 异步镜像
OpenTelemetry 全链路追踪 + Prometheus + Sentry
多租户中间件、三大方法论引擎（MEDDPICC/SPIN/Challenger）
四、简历写法建议
投递 AI 工程师 / LLM 应用工程师 / 算法工程师（NLP/AI Agent） 类岗位，以下几点最有竞争力：

简历项目描述模板
SalesBoost — AI 销售赋能平台（多智能体系统）

核心开发者 | Python / FastAPI / LangGraph / React | 2025–2026

重点突出以下几点（按优先级排序）：

① LangGraph 多智能体编排（最稀缺）
"基于 LangGraph StateGraph 设计并实现多智能体执行引擎，协调 Coach / SDR / Compliance / NPC 等 7 类专职 Agent 协同完成销售对话全流程，支持 Feature Flag 动态引擎切换与 Human-in-the-Loop 审核工作流"

② Hybrid GraphRAG（技术深度）
"实现 LLM 驱动的实体关系抽取 + 知识图谱多跳推理（3 hop），结合 BM25 + Dense（BAAI/BGE-M3）+ Reranker 混合检索，构建销售知识图谱 RAG 系统"

③ RLAIF 数据飞轮（前沿方向）
"设计 RLAIF（Reinforcement Learning from AI Feedback）闭环管道：自动采样 → Claude 3.5 标注 → 训练数据生成 → 模型微调，实现 AI 自我持续改进"

④ 实时 AI Copilot（业务价值+技术落地）
"设计 Live Assist 三阶段决策链（意图识别 → 阶段推断 → 策略生成），单次 LLM 调用完成全流程，目标延迟 <2s，支持 MEDDPICC/SPIN/Challenger 三大销售方法论"

⑤ 生产级架构（展现工程能力）
"全栈实现：FastAPI async + PostgreSQL (SQLAlchemy 2.0) + Qdrant 向量数据库 + Redis 分布式信号量 + OpenTelemetry 全链路追踪，支持多租户水平扩展"

投递不同岗位的侧重点
目标岗位	重点突出
AI Agent / LLM 应用工程师	LangGraph 编排、多 Agent 协作、Memory 架构、Constitutional AI
算法工程师（NLP）	GraphRAG、Hybrid Retrieval、RLAIF、PPO Reward Model
后端工程师（AI方向）	FastAPI + LangGraph 生产部署、Model Gateway、多租户、OTel
全栈工程师	Python FastAPI + React TypeScript + WebSocket 实时通信全栈
AI产品/技术经理	Data Flywheel 业务闭环设计、三大销售方法论集成、系统架构决策
一句话总结（面试开场）
"我开发了一个基于 LangGraph 的多智能体销售赋能平台，集成了 GraphRAG 知识检索、RLAIF 数据飞轮、Constitutional AI 价值对齐，以及实时 AI Copilot 功能，覆盖从 Agent 编排到生产监控的完整 AI 系统工程。"

