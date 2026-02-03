# SalesBoost 满分版控制系统架构设计 (Advanced Control System Architecture Design)

基于“闭环控制系统 + 策略显式化 + 证据链”的销冠能力复制方案。

## 0. 设计理念：从“聊天”到“决策控制”
系统不再仅仅是多智能体对话，而是一个**闭环决策系统**。核心任务是：
1. **状态估计 (State Estimation)**：实时感知客户心理与销售阶段。
2. **策略选择 (Policy Selection)**：从策略库中选择最优打法。
3. **安全约束 (Safety Constraints)**：确保输出 100% 合规且准确。

---

## 1. 核心架构：4 职能中心 + 2 系统层

### 1.1 四个职能中心 (Functional Centers)
1. **Director (战略层/编排器)**:
   - 职责：意图识别、阶段机管理、并发调度、策略仲裁。
   - 边界：不产出业务文本，只做路由与决策。
2. **Simulator (表现层/客户世界模型)**:
   - 职责：生成客户回应、模拟情绪变化、输出接受度事件。
   - 边界：不参与事实判断或策略建议。
3. **Mentor (战术层/策略生成器)**:
   - 职责：基于事实生成 **Strategy Objects (策略对象)**、话术候选、风险点预警。
   - 边界：不负责最终合规裁决。
4. **Auditor (约束层/合规门)**:
   - 职责：强制拦截、改写违规内容、解释原因、标注风险标签。
   - 边界：不参与策略选择。

### 1.2 两个系统层 (System Layers) - 满分关键
1. **Blackboard / Shared State (共享黑板)**:
   - 系统的真相来源。存储：当前阶段、客户心理状态、已尝试策略及其效果、引用证据、风险标签。
2. **Evidence & Telemetry (证据链与观测)**:
   - 决策溯源：每一条建议必须附带 `evidence_ids` (RAG/DB 引用) 和 `decision_trace` (决策链路)。

---

## 2. 策略显式化：Strategy Object
Mentor 不再直接输出建议文本，而是输出结构化的 **Strategy Object**，供 Director 仲裁。

### Strategy Object 核心字段
- `strategy_id`: 销冠打法 ID (如：SPIN 提问法、价值锚定法)。
- `hypothesis`: 策略适用理由（基于当前客户状态的假设）。
- `expected_effect`: 预期改变的变量（如：信任度 +0.2, 价格阻力 -0.5）。
- `script_candidates`: 2-3 个候选话术。
- `evidence`: 引用依据（RAG 证据片段或 DB 版本）。
- `risks`: 潜在合规风险点。

---

## 3. 执行模型：Turn Loop 控制循环
每一轮对话（Turn）都是一次完整的控制循环：

1. **Observe (观察)**: 接收学员输入，同步 Blackboard 中的最新状态。
2. **Plan (规划 - Director)**: 判定意图与阶段，决定并发分支。
3. **Parallel (并行)**:
   - **Simulator**: 生成客户回应 + 情绪/信任度事件。
   - **Mentor**: 检索事实 + 匹配策略库 -> 产出多个 Strategy Objects。
4. **Constrain (约束 - Auditor)**: 对所有候选内容进行合规裁决（阻断/改写）。
5. **Decide (决策 - Director)**: 策略仲裁。在合规的候选策略中选出最优项。
6. **Act (执行)**: 输出给学员，并记录“是否采纳”信号。
7. **Learn (学习)**: 更新 Blackboard。记录阶段迁移、状态变化、策略效果。

---

## 4. 关键产物 (Traceability)
系统必须持久化以下产物以支撑持续迭代：
- `state_timeline`: 客户状态/阶段的变化曲线。
- `strategy_trace`: 策略仲裁日志（候选策略 vs 选中策略及其原因）。
- `evidence_pack`: 事实引用的原始依据。
- `adoption_signal`: 学员对建议的采纳率闭环。

---

## 5. 工具层级设计 (Layered Tool Calling)
工具不再直接由 Agent 调用，而是分层管理：

- **事实/策略类 (Mentor 专用)**: `kb_retriever`, `facts_db_get`, `strategy_matcher`。
- **场景/情绪类 (Simulator 专用)**: `persona_provider`, `emotion_sim`。
- **约束/评估类 (Auditor/Director 专用)**: `compliance_guard`, `competency_eval`。
- **系统基础设施**: `semantic_cache`, `trace_log`。
