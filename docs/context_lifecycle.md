# Context Lifecycle & Self-Healing

## Overview
This document describes the end-to-end lifecycle for SalesBoost context:
- Context production (scoring + compression)
- Redis Streams replay for recovery
- Self-healing on reconnect
- Long-term memory consolidation
- Model lifecycle governance (Shadow -> Candidate -> Primary)

## State Replay & Self-Healing Flow

```mermaid
flowchart TD
    A[User Turn] --> B[Context Manager]
    B --> C[Score + Compression]
    C --> D[S1/S2/S3 Memory]
    C --> E[SalesState Stream]
    E --> F[Redis Streams]

    subgraph Recovery
        G[WebSocket Reconnect] --> H[Replay Engine]
        H --> I[Load Snapshot]
        I --> J[Replay Stream Events]
        J --> K[Recovered SalesState]
        K --> L[RECOVERY_SYNC to UI]
        H -->|Fail| M[Cold Start from S3]
    end
```

## Replay Engine Design
- **Inputs**: `session_id`, optional snapshot
- **Process**: replay Redis Streams in order; de-dup by `turn_id`
- **Output**: recovered `SalesState` with consistent stage + facts
- **Idempotency**: repeated events are ignored

## Self-Healing Guarantees
- Reconnect always attempts Replay first
- If Redis unavailable, fallback to S3 summary
- UI receives `RECOVERY_SYNC` with:
  - current stage
  - confirmed facts
  - compressed summary

## Long-Term Memory Consolidation
- Session finish triggers S3 aggregation
- Extract:
  - high-frequency errors
  - strengths / skill tags
  - compliance flags
- Store as student profile for next session bias

## Model Lifecycle Governance

```mermaid
stateDiagram-v2
    [*] --> SHADOW
    SHADOW --> CANDIDATE: EffectiveScore > Primary * 1.15
    CANDIDATE --> PRIMARY: Sustained + low risk
    PRIMARY --> ACTIVE: Underperform vs candidate
    ACTIVE --> QUARANTINED: SuccessRate < 0.7
    QUARANTINED --> [*]
```

### Rules Summary
- **EffectiveScore** = model_score * intent_weight * success_rate
- **Promotion** requires min calls + success rate threshold
- **Auto-quarantine** when success rate < 0.7
- **Anomaly** if score drop >= 2.0

## Lifecycle Job (Background)
- **Job**: `LifecycleJob` runs on a timer in the background task manager.
- **Inputs**: model history, success window, intent distribution.
- **Outputs**: lifecycle action, anomaly status, audit log event.
