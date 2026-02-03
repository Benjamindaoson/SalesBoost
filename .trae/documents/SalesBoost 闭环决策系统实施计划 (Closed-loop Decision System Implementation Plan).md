# SalesBoost 闭环决策系统实施计划 (Closed-loop Decision System Implementation Plan)

基于“5+1 智能体”架构与“策略显式化”原则，将系统从线性流水线升级为闭环控制系统。

## 1. 核心目标
1. **状态驱动**：建立统一的 Blackboard 共享状态。
2. **策略显式化**：实现 Strategy Object 的生成与仲裁。
3. **闭环控制**：基于 LangGraph 实现 Observe-Plan-Parallel-Constrain-Decide-Act 循环。
4. **证据可追溯**：确保每一项建议都有 RAG/DB 证据支撑。

---

## 2. 任务阶段划分

### 阶段一：基础设施与状态管理 (Blackboard & Librarian)
- [ ] **定义 Blackboard Schema**: 扩展现有 [fsm.py](file:///d:\SalesBoost\app\schemas\fsm.py)，支持心理状态、策略历史与证据链存储。
- [ ] **重构 Librarian (Context Manager)**: 将其接入 Blackboard，实现实时的状态估计（心理值变化、意图识别）。
- [ ] **持久化层升级**: 确保 Blackboard 状态在 Redis 中的原子性读写。

### 阶段二：工具层级化与证据链 (Tool Registry)
- [ ] **建立 Tool Registry**: 实现统一的工具调用入口，支持权限校验。
- [ ] **事实类工具升级**: 修改 `retriever.py`，输出带 `chunk_id` 和 `source` 的证据包。
- [ ] **策略类工具实现**: 实现 `strategy_matcher` 插件，对接 8 大环节策略库。

### 阶段三：智能体角色重构 (Specialized Agents)
- [ ] **Mentor 重构**: 修改 [coach_agent.py](file:///d:\SalesBoost\app\agents\ask\coach_agent.py)，使其输出 [strategy.py](file:///d:\SalesBoost\app\schemas\strategy.py) 定义的 Strategy Object。
- [ ] **Simulator 增强**: 修改 [npc_simulator.py](file:///d:\SalesBoost\app\agents\practice\npc_simulator.py)，增加情绪事件输出字段。
- [ ] **Auditor 独立化**: 实现专用的合规审计 Agent，支持拦截与重写。

### 阶段四：LangGraph 编排实现 (Orchestration)
- [ ] **定义 Graph 拓扑**: 基于 [LANGGRAPH_EXECUTION_FLOW.md](file:///d:\SalesBoost\docs\architecture\LANGGRAPH_EXECUTION_FLOW.md) 编写节点代码。
- [ ] **实现策略仲裁 (Decide Node)**: 在 Director 中编写逻辑，根据预期效果选择最优 Strategy Object。
- [ ] **集成并发执行**: 实现 Simulator 与 Mentor 的异步并发调用。

### 阶段五：闭环反馈与评估 (Closing the Loop)
- [ ] **实现 Evaluator Agent**: 开发课后评估逻辑，对比 Blackboard 中的初始状态与最终状态。
- [ ] **采纳率埋点**: 记录学员对 Strategy Object 的采纳信号，回馈至策略库。

---

## 3. 技术关键点
- **不变量约束**: 任何输出必须强制流经 Auditor 节点。
- **证据引用**: `evidence_pack` 必须在 WebSocket 消息中透明化，供前端展示。
- **可回放性**: 每一轮 Turn 的全量 Blackboard 快照需存入 `decision_trace`。

---

**请确认以上计划，确认后我将首先开始“阶段一：基础设施与状态管理”的实施。**
