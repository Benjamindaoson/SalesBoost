# Enterprise AI Memory System Architecture Design

## 1. Architecture Vision
To support enterprise-scale AI applications with 10M+ concurrent users, we define a **Multi-Layered Memory Architecture (MLMA)**. This system ensures millisecond latency for active sessions while maintaining deep, evolving knowledge about users and domains over time.

### 1.1 The Three Tiers

| Tier | Technology | Purpose | Latency | Capacity | Data Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Short-term (L1)** | **Redis Cluster** | Session Context, Working Memory | < 5ms | GBs | Key-Value, Streams, Lists |
| **Medium-term (L2)** | **Qdrant / Milvus** | Semantic History, User Preferences | < 50ms | TBs | High-dim Vectors (Embeddings) |
| **Long-term (L3)** | **Neo4j / Nebula** | Knowledge Graph, Relationship Reasoning | < 100ms | PBs | Nodes, Edges, Properties |

---

## 2. Core Requirements & Implementation

### 2.1 Data Models

#### L1: Short-term Memory (Redis)
*   **Session State:** `session:{session_id}:state` (Hash)
    *   `current_stage`: string
    *   `turn_count`: int
    *   `last_active`: timestamp
*   **Context Buffer:** `session:{session_id}:buffer` (List)
    *   Stores last N turns (raw text) for immediate context window construction.
*   **Dirty Flags:** `user:{user_id}:dirty` (Set)
    *   Tracks modified profile attributes that need syncing to L2/L3.

#### L2: Medium-term Memory (Vector DB)
*   **Collection:** `user_memories`
*   **Payload Schema:**
    ```json
    {
      "user_id": "uuid",
      "memory_type": "preference | fact | experience",
      "content": "User prefers concise answers",
      "vector": [0.12, -0.05, ...],
      "timestamp": 1706500000,
      "importance": 0.85
    }
    ```

#### L3: Long-term Memory (Graph DB)
*   **Nodes:** `User`, `Topic`, `Preference`, `Product`, `Constraint`
*   **Edges:**
    *   `(User)-[:INTERESTED_IN {weight: 0.9}]->(Topic)`
    *   `(User)-[:HAS_CONSTRAINT]->(Constraint)`
    *   `(Topic)-[:RELATED_TO]->(Product)`

### 2.2 Synchronization Mechanism (The "Memory Pipeline")

We implement a **Write-Back with Checkpointing** strategy to ensure performance and consistency.

1.  **Real-time Write (L1):** All agent interactions write immediately to Redis.
2.  **Async Consolidation (L1 -> L2):**
    *   **Trigger:** End of session OR Buffer full (e.g., every 10 turns).
    *   **Process:**
        1.  `MemoryConsolidator` reads Redis buffer.
        2.  LLM summarizes key facts/preferences.
        3.  Embed summary -> Insert into Vector DB (L2).
3.  **Knowledge Distillation (L2 -> L3):**
    *   **Trigger:** Scheduled Job (Nightly) or High-Importance Event.
    *   **Process:**
        1.  Analyze new Vector entries.
        2.  Extract entities and relations (GraphRAG).
        3.  Update Knowledge Graph (L3).

### 2.3 Incremental Profile Update Algorithm

To avoid re-computing the entire user profile, we use a **Delta-Merge Algorithm**:

1.  **Fetch Current Profile (P_t):** Retrieve aggregated profile from L2/L3.
2.  **Extract Delta (ΔP):** Identify *new* information in current session.
    *   e.g., "User mentioned they are now a Team Lead" (Old: Senior Dev).
3.  **Conflict Resolution:**
    *   If `New.Confidence > Old.Confidence`: Update.
    *   If `New.Timestamp > Old.Timestamp` AND `New` contradicts `Old`: Update (User changed).
    *   If ambiguous: Flag for clarification.
4.  **Apply Update:** `P_{t+1} = P_t + ΔP`.

---

## 3. Technical Specifications

### 3.1 Distributed Deployment & Consistency
*   **Redis:** Cluster mode with AOF persistence (fsync every sec). Multi-AZ deployment.
*   **Vector/Graph:** Sharding by `user_id` hash.
*   **CAP Theorem Trade-off:** CP for L1 (Consistency), AP for L2/L3 (Availability/Partition tolerance).
*   **Cross-Region Sync:**
    *   Active-Passive replication for L2/L3.
    *   L1 is region-local (sticky sessions).

### 3.2 Privacy & Security (GDPR)
*   **Data Isolation:** Logical isolation via `tenant_id`.
*   **Right to be Forgotten:** API endpoint `DELETE /user/{id}/memory` triggers cascade delete across Redis, Vector, and Graph.
*   **Encryption:** AES-256 at rest, TLS 1.3 in transit.
*   **PII Masking:** Automatic PII detection and redaction before storing in L2/L3 (unless explicitly authorized).

### 3.3 Backup & Disaster Recovery
*   **Point-in-Time Recovery (PITR):** Enabled for Graph DB.
*   **Snapshots:** Daily snapshots for Vector Indices.
*   **Replay:** Message Queue (Kafka/Redis Streams) retains 7 days of raw interaction logs to rebuild memory state if needed.

## 4. Interfaces (Python)

```python
class MemoryStore(ABC):
    @abstractmethod
    async def get(self, key: str): ...
    @abstractmethod
    async def put(self, key: str, value: Any): ...

class ShortTermMemory(MemoryStore):
    # Redis implementation
    pass

class MediumTermMemory(MemoryStore):
    # Vector DB implementation
    @abstractmethod
    async def search(self, query_vector, limit=5): ...

class LongTermMemory(MemoryStore):
    # Graph DB implementation
    @abstractmethod
    async def query_subgraph(self, center_node_id, depth=2): ...

class MemoryOrchestrator:
    # Manages sync and retrieval across tiers
    pass
```
