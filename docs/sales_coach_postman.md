# Sales Coach API - Postman 测试说明

## 1. POST `/api/v1/coach/process`

**URL:** `http://localhost:8000/api/v1/coach/process`  
**Method:** `POST`  
**Headers:** `Content-Type: application/json`

### 示例请求体 (JSON)

```json
{
  "session_id": "test-session-001",
  "history": [
    { "role": "sales", "content": "您好，请问是张先生吗？我是 XX 银行信用卡中心的。" },
    { "role": "customer", "content": "嗯，什么事？" },
    { "role": "sales", "content": "想跟您介绍一张我们行的白金卡，出差权益很实用。" },
    { "role": "customer", "content": "年费多少？太贵我就不办了。" }
  ],
  "text_stream": null,
  "current_context": {},
  "turn_number": 1
}
```

### 可选：仅追加本句转写

若只推送当前句 `text_stream`，历史来自前端缓存时：

```json
{
  "session_id": "test-session-001",
  "history": [
    { "role": "customer", "content": "年费多少？太贵我就不办了。" }
  ],
  "text_stream": "这张卡年费 900，但每年有 6 次接送机，算下来很值。",
  "current_context": null,
  "turn_number": 2
}
```

### 示例响应 (200)

```json
{
  "success": true,
  "phase": "权益说明",
  "detected_phase": "异议处理",
  "phase_transition_detected": true,
  "customer_intent": "关心年费成本，有拒绝意向",
  "action_advice": "先认同顾虑，再算权益覆盖成本（接送机、贵宾厅），引导回本。",
  "script_example": "您说得对，年费确实要算清楚。这张卡每年 6 次接送机、机场贵宾厅，您出差多的话，光这些就值回年费了。",
  "compliance_risk": null,
  "error": null
}
```

### 合规风险示例

当销售话术触发敏感词时，`compliance_risk` 非空：

```json
{
  "success": true,
  "phase": "权益说明",
  "detected_phase": "权益说明",
  "phase_transition_detected": false,
  "customer_intent": "询问额度",
  "action_advice": "【警报】检测到合规风险！请立即修正：禁止承诺具体额度，应以银行最终审批为准",
  "script_example": "额度由银行根据您的资质审批，我们这边没法承诺具体数字，您先填表，审批结果很快就会出来。",
  "compliance_risk": {
    "risk_level": "HIGH",
    "sensitive_words": ["额度"],
    "warning_message": "禁止承诺具体额度，应以银行最终审批为准"
  },
  "error": null
}
```

---

## 2. WebSocket `/api/v1/coach/ws/{session_id}`（预留）

**URL:** `ws://localhost:8000/api/v1/coach/ws/test-session-001`  
**说明:** 当前为占位实现，支持 `ping` / `pong`、`transcript_chunk` 占位回包。

- 连接成功后收到 `{"type": "connected", "session_id": "..."}`  
- 发送 `{"type": "ping"}` → 收到 `{"type": "pong"}`  
- 发送 `{"type": "transcript_chunk", ...}` → 收到 `{"type": "ack", "message": "transcript_chunk received (stub)"}`
