# SalesBoost Event Catalog

This document lists all asynchronous events supported by the `EventBus`.

## 1. Session Events (`session.*`)

| Event Type | Description | Payload Structure |
|------------|-------------|-------------------|
| `session.started` | Triggered when a new training session starts. | `SessionEventPayload` |
| `session.resumed` | Triggered when a suspended session is resumed. | `SessionEventPayload` |
| `session.suspended`| Triggered when a session is manually or automatically suspended. | `SessionEventPayload` |
| `session.completed`| Triggered when a session reaches its final stage. | `SessionEventPayload` |
| `session.timeout`  | Triggered when a session expires due to inactivity. | `SessionEventPayload` |

## 2. Workflow Events (`workflow.*`)

| Event Type | Description | Payload Structure |
|------------|-------------|-------------------|
| `workflow.stage_transition` | Triggered when the FSM moves to a new stage. | `WorkflowEventPayload` |
| `workflow.agent_switch`      | Triggered when switching between different agent roles. | `WorkflowEventPayload` |
| `workflow.turn_completed`    | Triggered after a full conversation turn is processed. | `WorkflowEventPayload` |

## 3. Audit & Security Events (`audit.*`)

| Event Type | Description | Payload Structure |
|------------|-------------|-------------------|
| `audit.sensitive_content_blocked` | Triggered when `StreamingGuard` blocks content. | `AuditEventPayload` |
| `audit.budget_exceeded`           | Triggered when a session/user exceeds token budget. | `AuditEventPayload` |
| `audit.compliance_violation`      | Triggered when `ComplianceAgent` detects a violation. | `AuditEventPayload` |

---

## Payload Definitions

### `EventBase`
Common fields for all events:
- `event_id`: UUID
- `timestamp`: UTC datetime
- `session_id`: Optional string
- `user_id`: Optional string
- `tenant_id`: Optional string

### `SessionEventPayload`
- `action`: String (e.g., "start", "stop")
- `metadata`: Key-value pairs

### `WorkflowEventPayload`
- `from_stage`: Previous FSM stage
- `to_stage`: Current FSM stage
- `agent_type`: Type of agent active
- `context_snapshot`: Serialized session context

### `AuditEventPayload`
- `reason`: Violation description
- `severity`: "low", "medium", "high", "critical"
- `blocked_content`: Snippet of blocked text
- `risk_score`: Numeric 0.0-1.0
