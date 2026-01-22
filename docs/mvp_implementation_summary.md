# MVP 实现总结

## 变更文件列表

### 后端新增文件
1. `app/schemas/mvp.py` - MVP Schema 定义
2. `app/services/intent_classifier.py` - 意图分类服务
3. `app/services/quick_suggest_service.py` - 快速建议服务
4. `app/services/micro_feedback_service.py` - 轻量复盘服务
5. `app/models/compliance_models.py` - 合规日志模型
6. `app/models/feedback_models.py` - 反馈模型
7. `app/api/endpoints/mvp_suggest.py` - 快速建议 API
8. `app/api/endpoints/mvp_compliance.py` - 合规检测 API
9. `app/api/endpoints/mvp_feedback.py` - 轻量复盘 API
10. `alembic/versions/mvp_add_compliance_and_feedback_tables.py` - 数据库迁移

### 后端修改文件
1. `app/schemas/agent_outputs.py` - 添加 `risk_level` 和 `safe_rewrite` 字段
2. `app/agents/compliance_agent.py` - 增强 `_generate_safe_rewrite()` 方法
3. `app/api/endpoints/websocket.py` - 集成快速建议和轻量复盘
4. `app/main.py` - 注册 MVP API 路由

### 前端新增文件
1. `frontend/src/components/mvp/QuickSuggestPanel.tsx` - 快速建议面板
2. `frontend/src/components/mvp/ComplianceGuard.tsx` - 合规防护组件
3. `frontend/src/components/mvp/MicroFeedbackCard.tsx` - 轻量复盘卡片

### 前端修改文件
1. `frontend/src/pages/PracticeRoom.tsx` - 集成 MVP 组件
2. `frontend/src/components/practice-room/MessageInput.tsx` - 支持 value/onChange

### 文档文件
1. `docs/mvp_gap_analysis.md` - 差距清单
2. `docs/mvp_acceptance.md` - 验收用例

---

## 关键接口请求/响应示例

### 1. 快速建议 API

**请求**:
```http
POST /api/v1/mvp/suggest
Content-Type: application/json

{
  "session_id": "abc-123",
  "last_user_msg": "这张卡有什么权益？",
  "optional_context": {}
}
```

**响应**:
```json
{
  "intent_label": "权益问答",
  "suggested_reply": "这张卡主要权益包括机场贵宾厅、酒店升级、积分兑换等。",
  "alt_replies": [
    "主要权益有：机场贵宾厅无限次使用、全球酒店升级、积分永久有效。",
    "权益包括机场贵宾厅、酒店升级、积分兑换，特别适合经常出差的您。"
  ],
  "confidence": 0.85,
  "evidence": {
    "source_titles": ["信用卡权益说明", "官方活动规则"],
    "source_snippets": ["机场贵宾厅...", "酒店升级..."]
  }
}
```

### 2. 合规检测 API

**请求**:
```http
POST /api/v1/mvp/compliance/check?session_id=abc-123&turn_number=5
Content-Type: application/json

{
  "text": "绝对能保证您稳赚不赔",
  "context": {}
}
```

**响应**:
```json
{
  "risk_level": "BLOCK",
  "risk_tags": ["exaggeration", "misleading"],
  "safe_rewrite": "根据过往经验，大多数情况下可以满足您的需求，但任何投资都有风险。",
  "original": "绝对能保证您稳赚不赔",
  "reason": "这句话有合规风险，建议这样说："
}
```

### 3. 轻量复盘 API

**请求**:
```http
GET /api/v1/mvp/sessions/abc-123/feedback
```

**响应**:
```json
{
  "feedback_items": [
    {
      "title": "异议处理后可推进",
      "what_happened": "您识别了客户的异议，但没有及时推进成交",
      "better_move": "在化解异议后，可以尝试推进：'既然您已经了解了权益，不如现在就办理，还能享受当前优惠'",
      "copyable_phrase": "既然您已经了解了权益，不如现在就办理，还能享受当前优惠"
    },
    {
      "title": "抓住推进时机",
      "what_happened": "客户表达了积极信号，但您没有及时给出明确的下一步",
      "better_move": "当客户表示同意时，立即给出具体行动：'太好了！我现在就帮您提交申请，请确认一下您的信息'",
      "copyable_phrase": "太好了！我现在就帮您提交申请，请确认一下您的信息"
    }
  ],
  "session_id": "abc-123",
  "total_turns": 8
}
```

### 4. WebSocket 消息格式（增强）

**turn_result 消息**（新增 `quick_suggest` 字段）:
```json
{
  "type": "turn_result",
  "turn": 3,
  "npc_response": "听起来不错，我再考虑一下",
  "quick_suggest": {
    "intent_label": "推进成交",
    "suggested_reply": "好的，我现在就帮您办理。请确认一下您的个人信息是否正确？",
    "alt_replies": [
      "太好了！我现在为您提交申请，预计3-5个工作日可以完成。",
      "没问题，我马上为您处理。您还有其他需要了解的吗？"
    ],
    "confidence": 0.8,
    "evidence": null
  },
  "compliance_risk_level": "OK",
  "compliance_safe_rewrite": null
}
```

**session_complete 消息**（新增 `micro_feedback` 字段）:
```json
{
  "type": "session_complete",
  "final_stage": "COMPLETED",
  "total_turns": 8,
  "message": "恭喜完成本次训练！",
  "micro_feedback": {
    "feedback_items": [
      {
        "title": "异议处理后可推进",
        "what_happened": "您识别了客户的异议，但没有及时推进成交",
        "better_move": "在化解异议后，可以尝试推进：'既然您已经了解了权益，不如现在就办理，还能享受当前优惠'",
        "copyable_phrase": "既然您已经了解了权益，不如现在就办理，还能享受当前优惠"
      }
    ],
    "total_turns": 8
  }
}
```

---

## 运行方式

### 1. 数据库迁移
```bash
# 运行迁移，创建 compliance_logs 和 session_feedbacks 表
alembic upgrade head
```

### 2. 启动后端
```bash
# 安装依赖（如果新增）
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 启动前端
```bash
cd frontend
npm install  # 如果需要安装新依赖
npm run dev
```

### 4. 测试流程
1. 访问 `http://localhost:5173`（前端）
2. 创建会话或连接已有会话
3. 发送消息，观察快速建议面板
4. 在输入框输入违规内容，观察合规检测
5. 完成会话，查看轻量复盘卡片

---

## 产品体验保障措施

### 1. "短输出"保障
- ✅ `QuickSuggestService._truncate_to_220_chars()` 强制截断到220字符
- ✅ `CoachAgent` 输出时强制短句格式
- ✅ Schema 验证：`suggested_reply` 字段 `max_length=220`

### 2. "不打断"保障
- ✅ 合规检测 debounce 500ms（`ComplianceGuard` 组件）
- ✅ 快速建议通过 WebSocket 异步返回，不阻塞用户输入
- ✅ 前端组件使用 `useEffect` + `setTimeout` 实现 debounce

### 3. "可复制"保障
- ✅ `QuickSuggestPanel` 提供"复制发送"按钮，一键填入输入框
- ✅ `MicroFeedbackCard` 每条反馈提供"复制句子"按钮
- ✅ `ComplianceGuard` 提供"一键替换"按钮，直接替换输入框内容
- ✅ 所有话术字段都是纯文本，无格式标记

### 4. 降级策略
- ✅ RAG 无来源时，返回安全兜底文案（不编造）
- ✅ 合规检测失败时，Fail-closed（返回 BLOCK）
- ✅ 快速建议生成失败时，返回通用建议（不报错）

---

## 数据持久化

### 合规日志表 (`compliance_logs`)
```sql
CREATE TABLE compliance_logs (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    turn_number INTEGER NOT NULL,
    original TEXT NOT NULL,
    rewrite TEXT,
    risk_tags JSON,
    risk_level VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### 会话反馈表 (`session_feedbacks`)
```sql
CREATE TABLE session_feedbacks (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE,
    feedback_items JSON NOT NULL,
    total_turns INTEGER NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### 消息表扩展 (`messages`)
- 新增字段：`suggested_reply TEXT`（存储建议话术）

---

## 关键函数单测建议

### 1. 合规检测
```python
# tests/test_compliance_detection.py
def test_block_high_risk():
    agent = ComplianceAgent()
    result = await agent.check("绝对能保证您稳赚不赔", SalesStage.OBJECTION_HANDLING)
    assert result.risk_level == "BLOCK"
    assert result.safe_rewrite is not None
    assert len(result.safe_rewrite) <= 220

def test_warn_medium_risk():
    agent = ComplianceAgent()
    result = await agent.check("很多客户都在用", SalesStage.OBJECTION_HANDLING)
    assert result.risk_level == "WARN"
    assert result.safe_rewrite is not None
```

### 2. 建议生成
```python
# tests/test_quick_suggest.py
def test_benefit_qa_with_source():
    service = QuickSuggestService()
    result = await service.generate_suggest(...)
    assert result.intent_label == IntentLabel.BENEFIT_QA
    assert len(result.suggested_reply) <= 220
    assert len(result.alt_replies) >= 2
    assert result.evidence is not None

def test_benefit_qa_without_source():
    # RAG 无结果时，应该返回降级文案
    service = QuickSuggestService()
    result = await service.generate_suggest(...)
    assert result.intent_label == IntentLabel.BENEFIT_QA
    assert result.evidence is None
    assert "官方" in result.suggested_reply or "客服" in result.suggested_reply
```

### 3. 反馈生成
```python
# tests/test_micro_feedback.py
def test_feedback_max_3_items():
    service = MicroFeedbackService()
    result = await service.generate_feedback(session_id, db)
    assert len(result.feedback_items) <= 3
    for item in result.feedback_items:
        assert item.copyable_phrase is not None
        assert len(item.copyable_phrase) > 0
```

---

## 配置项（环境变量）

### 合规检测
- `COMPLIANCE_RISK_THRESHOLD` - 风险阈值（默认：high=BLOCK, medium=WARN）
- `COMPLIANCE_SAFE_REWRITE_MAX_LENGTH` - 安全改写最大长度（默认：220）

### 快速建议
- `QUICK_SUGGEST_MAX_LENGTH` - 建议话术最大长度（默认：220）
- `QUICK_SUGGEST_MIN_ALT_REPLIES` - 最少备用话术数量（默认：2）

### 轻量复盘
- `MICRO_FEEDBACK_MAX_ITEMS` - 最多反馈条数（默认：3）

---

## 安全与降级

### 1. 不确定信息不编造
- ✅ `QuickSuggestService._generate_benefit_qa_suggest()` 中，RAG 无结果时返回降级文案
- ✅ 降级文案明确引导用户查看官方渠道
- ✅ `confidence` 降低到 0.5（表示不确定性）

### 2. Fail-Closed 策略
- ✅ 合规检测失败时，返回 `BLOCK`（`mvp_compliance.py`）
- ✅ 快速建议生成失败时，返回通用建议（不报错）

### 3. 输入验证
- ✅ `prompt_guard.detect()` 已在 Orchestrator 中调用
- ✅ 合规检测对所有用户输入进行验证

---

## 验收检查清单

- [ ] 用例1：权益问答返回带来源的短回复
- [ ] 用例2：异议处理返回可复制话术 + 换一句可切换
- [ ] 用例3：推进成交识别推进时机并给推进句
- [ ] 用例4：输入违规承诺 BLOCK + 给安全改写 + 发送被禁用
- [ ] 用例5：灰区表达 WARN + 给改写可一键替换
- [ ] 用例6：会话结束弹出<=3条复盘反馈
- [ ] 用例7：日志落库能查到合规事件与反馈
- [ ] 用例8：降级策略 RAG无来源时不胡编

---

## 后续优化建议（非MVP范围）

1. **意图分类优化**：使用轻量模型（如 BERT-tiny）提升分类准确度
2. **建议生成优化**：使用模板库 + LLM 生成，确保话术质量
3. **合规规则扩展**：支持从配置文件/数据库动态加载规则
4. **反馈规则扩展**：支持自定义反馈规则和模板
5. **性能优化**：缓存 RAG 结果，减少重复检索

