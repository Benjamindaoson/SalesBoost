# SalesBoost Cloud-Native Architecture

## Overview
This document outlines the high-availability, scalable, and secure cloud-native architecture for the SalesBoost platform. The system is designed based on Silicon Valley best practices, utilizing an Event-Driven Architecture (EDA) to decouple components and ensure resilience.

## Core Design Principles

### 1. High Availability (HA) & Resilience
- **Stateless Services**: All microservices and API nodes are stateless, allowing for seamless horizontal scaling and zero-downtime deployments.
- **Fault Isolation**: Services are decoupled via an asynchronous Event Bus. A failure in one service (e.g., Audit) does not block the critical path of others (e.g., API).
- **Graceful Degradation**: The system is designed to continue operating even if non-essential subsystems fail.

### 2. Scalability
- **Asynchronous Event Bus**: Core communication is handled by a high-performance, non-blocking Pub/Sub mechanism (`app.infra.events.bus`).
- **Concurrency**: Python's `asyncio` is leveraged to handle thousands of concurrent connections per node.
- **Horizontal Scaling**: Components can be scaled independently based on load (e.g., scaling the Workflow Engine separately from the API Gateway).

### 3. Security
- **Zero Trust Principles**: Every request is authenticated and authorized.
- **Audit Trails**: Critical actions are asynchronously logged via the Audit Service, triggered by immutable events.
- **Schema Validation**: All internal and external communication is strictly validated using Pydantic schemas to prevent injection attacks and data corruption.

## System Architecture

### Layers

1.  **API Layer (Edge)**
    - **Technology**: FastAPI
    - **Responsibility**: Request validation, Authentication, Routing.
    - **Refactoring**: Decoupled from core logic using the Event Bus. Endpoints publish events rather than calling services directly.
    - **Middleware**: Context injection (Tenant ID), Tracing, and Security headers.

2.  **Event Bus (Backbone)**
    - **Implementation**: In-memory Async Pub/Sub (extensible to Redis/Kafka).
    - **Features**:
        - Decorator-based subscription (`@bus.subscribe`).
        - Request-Response pattern for async RPC.
        - Non-blocking concurrency with `asyncio.gather`.
        - Distributed Tracing integration.

3.  **Service Layer (Core)**
    - **Audit Service**: Listens for security and compliance events.
    - **Workflow Engine**: Orchestrates business logic based on state changes.
    - **Session Manager**: Manages user session lifecycles.

4.  **Observability Layer**
    - **Distributed Tracing**: `ExecutionTracer` captures full request lifecycles across event boundaries.
    - **Structured Logging**: JSON-formatted logs for ingestion by aggregation tools.

## Event-Driven Patterns

### Publish/Subscribe (Redis Streams)
Used for reliable, high-throughput event distribution. Supports Consumer Groups for parallel processing.
- **Fan-out**: Events like `KNOWLEDGE_UPDATED` are distributed to multiple consumer groups (e.g., `chroma-indexer`, `bm25-indexer`) to ensure hybrid search consistency.
```python
await bus.publish(EventType.KNOWLEDGE_UPDATED, payload)
```

### Request-Response (Async RPC)
Used when a response is required from an asynchronous service.
- **Implementation**: Request sent via Stream; Response returned via ephemeral Redis Channel or List.
```python
response = await bus.request(EventType.GET_USER_STATUS, payload)
```

### Reliability & Retry
- **Logic Consistency**: `ConsistencyChecker` validates LLM outputs. On failure, a `RETRY_EVALUATION` event is published with correction prompts (Delay Queue/Dead Letter pattern).
- **Persistence**: Redis AOF (Everysec) ensures audit logs and critical events are not lost on crash.

## Traffic Management
- **Intelligent Routing**: `ModelGateway` uses a Redis-based Rate Limiter.
- **Circuit Breaking**: Protects external Model APIs from overload.

## Security & Compliance
- **Audit Logging**: The `AuditService` automatically captures `SENSITIVE_CONTENT_BLOCKED` and other critical events.
- **Type Safety**: Pydantic models ensure that malformed data is rejected at the system boundary.

## Future Roadmap
- **Containerization**: Dockerize all components for Kubernetes deployment.
- **Service Mesh**: Introduce Istio/Linkerd for advanced traffic management.
