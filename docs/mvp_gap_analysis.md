# MVP 差距清单

## 1. 会话/消息数据结构 ✅
- **文件路径**: `app/models/runtime_models.py`
- **现状**: 
  - ✅ `Session` 表已存在，包含 session_id, user_id, status 等字段
  - ✅ `Message` 表已存在，包含 content, role, turn_number, compliance_result 等字段
- **缺什么**: 
  - 需要扩展 Message 表，添加 `suggested_reply` 字段存储建议话术
  - 需要新增 `ComplianceLog` 表存储合规事件（original/rewrite/tags）
  - 需要新增 `SessionFeedback` 表存储轻量复盘结果
- **怎么补**: 
  - 创建数据库迁移，添加新字段和新表
  - 在 Message 模型中添加 `suggested_reply: Optional[str]` 字段

## 2. WebSocket/HTTP入口 ✅
- **文件路径**: `app/api/endpoints/websocket.py`
- **现状**: 
  - ✅ WebSocket 端点 `/ws/train` 已存在
  - ✅ 支持实时消息收发
- **缺什么**: 
  - 需要新增 HTTP API `/api/v1/suggest` 用于"给一句可直接发送的话术"（可选，也可通过WS事件）
  - 需要新增 HTTP API `/api/v1/compliance/check` 用于实时合规检测（debounce调用）
  - 需要新增 HTTP API `/api/v1/sessions/{session_id}/feedback` 用于获取轻量复盘
- **怎么补**: 
  - 在 `app/api/endpoints/` 下创建 `suggest.py` 和 `compliance.py`
  - 复用现有 WebSocket 流程，在 `turn_result` 消息中包含建议话术

## 3. Agent编排 ✅
- **文件路径**: `app/services/orchestrator.py`
- **现状**: 
  - ✅ Orchestrator 已存在，协调 IntentGate/NPC/Coach/Evaluator/RAG/Compliance
  - ✅ Turn Loop 流程完整
- **缺什么**: 
  - CoachAgent 输出格式需要调整为"一句话话术"（<=220字符，2段以内）
  - 需要新增 `IntentLabel` 分类（权益问答/异议处理/推进成交/合规风险/其他）
  - 需要确保建议输出包含 `alt_replies`（至少2条备用）
  - 需要确保 RAG 结果包含来源追溯（source_titles, source_snippets）
- **怎么补**: 
  - 修改 `CoachAgent.generate_advice()` 方法，强制输出短句
  - 新增 `IntentClassifier` 服务，基于规则/轻模型分类
  - 修改 RAG 输出格式，确保包含来源信息

## 4. 合规模块 ✅
- **文件路径**: `app/agents/compliance_agent.py`
- **现状**: 
  - ✅ ComplianceAgent 已存在
  - ✅ 已有规则引擎（HIGH_RISK_PATTERNS, MEDIUM_RISK_PATTERNS）
  - ✅ 已有 `safe_alternative` 字段
- **缺什么**: 
  - 需要增强 `_sanitize_message()` 方法，生成完整的 `safe_rewrite`（短句，可直接替换）
  - 需要添加 `risk_level` enum（OK/WARN/BLOCK）
  - 需要确保 BLOCK 时返回完整的改写版本
  - 需要添加合规事件日志落库
- **怎么补**: 
  - 修改 `ComplianceOutput` schema，添加 `risk_level` 和 `safe_rewrite` 字段
  - 增强 `_sanitize_message()` 方法，生成完整改写版本
  - 创建 `ComplianceLog` 模型并落库

## 5. 评估模块 ✅
- **文件路径**: `app/agents/evaluator_agent.py`
- **现状**: 
  - ✅ EvaluatorAgent 已存在
  - ✅ 已有评分和维度分析
- **缺什么**: 
  - 需要新增 `generate_micro_feedback()` 方法，输出<=3条可执行反馈
  - 反馈格式：{title, what_happened, better_move, copyable_phrase}
  - 需要规则优先，避免长篇报告
- **怎么补**: 
  - 创建 `app/services/micro_feedback_service.py`
  - 基于规则生成反馈（如"出现异议但未推进"等）
  - 复用 Evaluator 维度，但压缩为<=3条

## 6. 前端 ✅
- **文件路径**: `frontend/src/pages/PracticeRoom.tsx`
- **现状**: 
  - ✅ PracticeRoom 组件已存在
  - ✅ WebSocket 连接已实现
  - ✅ 消息列表和输入框已存在
- **缺什么**: 
  - 需要新增"实时辅助面板"（展示 intent_label, suggested_reply, 复制发送/换一句按钮）
  - 需要输入框 debounce 500ms 调用合规检测
  - 需要合规检测结果展示（WARN/BLOCK + 一键替换）
  - 需要会话结束后弹出"轻量复盘"卡片（<=3条反馈）
- **怎么补**: 
  - 创建 `frontend/src/components/mvp/QuickSuggestPanel.tsx`
  - 创建 `frontend/src/components/mvp/ComplianceGuard.tsx`
  - 创建 `frontend/src/components/mvp/MicroFeedbackCard.tsx`
  - 修改 PracticeRoom，集成新组件

## 7. 数据与日志 ⚠️
- **文件路径**: `app/models/` (需要新建)
- **现状**: 
  - ✅ Message 表可存储对话消息
- **缺什么**: 
  - 需要 `ComplianceLog` 表：{session_id, original, rewrite, risk_tags, ts}
  - 需要 `SessionFeedback` 表：{session_id, feedback_items[], created_at}
- **怎么补**: 
  - 创建 `app/models/compliance_models.py`
  - 创建 `app/models/feedback_models.py`
  - 创建数据库迁移

## 8. Prompt Guard ✅
- **文件路径**: `app/security/prompt_guard.py` (用户已添加引用)
- **现状**: 
  - ✅ 用户已在 orchestrator 中添加了 `prompt_guard.detect()` 调用
- **缺什么**: 
  - 需要确认该文件是否存在，如果不存在需要创建
- **怎么补**: 
  - 检查文件是否存在，不存在则创建基础实现

