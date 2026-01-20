# SalesBoost 技术架构文档

## 1. 架构设计

### 1.1 系统架构图

```mermaid
graph TD
    A[用户浏览器] --> B[FastAPI Web服务]
    B --> C[WebSocket连接管理器]
    B --> D[REST API端点]
    
    C --> E[会话编排器]
    D --> E
    
    E --> F[多智能体系统]
    F --> G[意图识别Agent]
    F --> H[NPC客户Agent]
    F --> I[教练Agent]
    F --> J[评估Agent]
    F --> K[RAG知识Agent]
    F --> L[合规Agent]
    
    E --> M[状态管理引擎]
    E --> N[能力追踪系统]
    E --> O[策略分析器]
    E --> P[课程规划器]
    
    M --> Q[SQLite数据库]
    N --> Q
    O --> Q
    P --> Q
    
    K --> R[ChromaDB向量库]
    
    S[Redis缓存] --> E
    S --> C
    
    subgraph "表现层"
        A
    end
    
    subgraph "网关层"
        B
        C
        D
    end
    
    subgraph "业务逻辑层"
        E
        F
        M
        N
        O
        P
    end
    
    subgraph "数据访问层"
        Q
        R
        S
    end
```

### 1.2 分层架构说明

#### 表现层（Presentation Layer）
- **技术栈**：HTML5 + Tailwind CSS + JavaScript
- **职责**：用户界面展示、交互处理、实时通信
- **特点**：响应式设计、WebSocket实时通信、移动端适配

#### 网关层（Gateway Layer）
- **技术栈**：FastAPI + WebSocket + JWT认证
- **职责**：
  - REST API接口管理
  - WebSocket连接管理
  - 请求路由和负载均衡
  - 认证授权和限流控制
- **核心组件**：
  - ConnectionManager：WebSocket连接状态管理
  - API Router：RESTful接口路由
  - Auth Middleware：JWT令牌验证

#### 业务逻辑层（Business Logic Layer）
- **技术栈**：Python + 异步编程
- **职责**：
  - 会话编排和状态管理
  - 多智能体协调
  - 销售能力评估
  - 个性化学习路径规划
- **核心组件**：
  - SessionOrchestrator：会话编排器（唯一写入入口）
  - FSMEngine：有限状态机引擎
  - Multi-Agent System：多智能体协同系统

#### 数据访问层（Data Access Layer）
- **技术栈**：SQLAlchemy + ChromaDB + Redis
- **职责**：
  - 关系型数据持久化
  - 向量数据存储和检索
  - 缓存和会话管理
- **存储系统**：
  - SQLite：业务数据存储（MVP阶段）
  - ChromaDB：知识库向量存储
  - Redis：缓存和分布式锁

## 2. 技术描述

### 2.1 核心技术栈

- **后端框架**：FastAPI 0.104+ (异步高性能Web框架)
- **编程语言**：Python 3.11+ (异步编程支持)
- **数据库**：SQLite 3.0+ (MVP) / PostgreSQL 14+ (生产)
- **缓存**：Redis 7.0+ (分布式缓存和会话存储)
- **向量数据库**：ChromaDB 0.4+ (知识库和语义搜索)
- **前端模板**：Jinja2 3.1+ (服务端渲染)
- **样式框架**：Tailwind CSS 3.0+ (现代化UI)

### 2.2 关键依赖库

```python
# Web框架和异步支持
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0

# 数据库和ORM
sqlalchemy==2.0.23
aiosqlite==0.19.0  # MVP阶段
asyncpg==0.29.0    # 生产环境
alembic==1.12.1    # 数据库迁移

# 缓存和消息队列
redis==5.0.1

# 向量数据库和AI
chromadb==0.4.18
openai==1.3.7
langchain==0.0.340
langgraph==0.0.40

# 认证和安全
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# 数据验证和序列化
pydantic==2.5.0
pydantic-settings==2.1.0

# 限流和监控
slowapi==0.1.9
```

### 2.3 技术选型依据

1. **FastAPI**：
   - 原生异步支持，适合高并发WebSocket场景
   - 自动API文档生成，便于前后端协作
   - 类型安全和自动验证，减少运行时错误

2. **SQLite → PostgreSQL迁移路径**：
   - MVP阶段使用SQLite快速验证产品概念
   - 生产环境平滑迁移到PostgreSQL，支持高并发
   - SQLAlchemy抽象层保证数据库无关性

3. **多智能体架构**：
   - 专业化分工，每个Agent专注特定领域
   - 可扩展性强，易于添加新的Agent角色
   - 支持并行处理，提高系统响应速度

## 3. 路由定义

### 3.1 API路由结构

| 路由 | 方法 | 用途 | 认证 |
|------|------|------|------|
| `/api/v1/auth/login` | POST | 用户登录 | 否 |
| `/api/v1/auth/register` | POST | 用户注册 | 否 |
| `/api/v1/sessions` | GET | 获取会话列表 | 是 |
| `/api/v1/sessions/{id}` | GET | 获取会话详情 | 是 |
| `/api/v1/scenarios` | GET | 获取场景配置 | 是 |
| `/api/v1/reports/progress` | GET | 学习进度报告 | 是 |
| `/api/v1/profile` | GET | 用户画像信息 | 是 |
| `/api/v1/admin/users` | GET | 管理员用户管理 | 是(Admin) |
| `/api/v1/admin/scenarios` | POST | 创建场景配置 | 是(Admin) |

### 3.2 WebSocket端点

```javascript
// WebSocket连接URL
ws://localhost:8000/ws/train?course_id=xxx&scenario_id=xxx&persona_id=xxx&token=xxx

// 消息格式
{
    "type": "user_message",
    "content": "客户说：我对你们的产品很感兴趣",
    "session_id": "uuid-v4"
}

// 响应格式
{
    "type": "turn_result",
    "npc_response": "客户回复内容",
    "coach_advice": "教练建议内容",
    "evaluation": {
        "score": 8.5,
        "dimensions": {
            "listening": 9.0,
            "questioning": 8.0,
            "value_proposition": 8.5
        }
    },
    "session_state": {
        "current_stage": "discovery",
        "turn_count": 5
    }
}
```

## 4. 接口设计

### 4.1 REST API规范

#### 认证机制
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "password123"
}

// 响应
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

#### 统一响应格式
```json
{
    "success": true,
    "data": {},
    "message": "操作成功",
    "timestamp": "2024-01-19T10:30:00Z",
    "request_id": "uuid-v4"
}

{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "输入参数验证失败",
        "details": {
            "field": "email",
            "message": "邮箱格式不正确"
        }
    },
    "timestamp": "2024-01-19T10:30:00Z",
    "request_id": "uuid-v4"
}
```

### 4.2 WebSocket协议

#### 连接建立
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/train?course_id=123&scenario_id=456&persona_id=789&token=xxx');

ws.onopen = function(event) {
    console.log('WebSocket连接已建立');
};
```

#### 消息类型定义
```typescript
interface WebSocketMessage {
    type: 'user_message' | 'system_command' | 'ping';
    content: string;
    session_id: string;
    timestamp: string;
}

interface WebSocketResponse {
    type: 'turn_result' | 'error' | 'session_complete' | 'pong';
    data: any;
    timestamp: string;
}
```

### 4.3 版本控制策略

- **URL版本控制**：`/api/v1/...`
- **向后兼容**：新版本发布时保持旧版本可用
- **废弃策略**：提前3个月通知API废弃
- **版本迁移工具**：提供自动化迁移脚本

## 5. 数据设计

### 5.1 实体关系图

```mermaid
erDiagram
    USER ||--o{ SESSION : creates
    USER ||--o{ USER_STRATEGY_PROFILE : has
    ORGANIZATION ||--o{ USER : contains
    ORGANIZATION ||--o{ COURSE : owns
    ORGANIZATION ||--o{ SCENARIO_CONFIG : configures
    
    COURSE ||--o{ SCENARIO_CONFIG : contains
    SCENARIO_CONFIG ||--o{ CUSTOMER_PERSONA : defines
    SCENARIO_CONFIG ||--o{ SESSION : instantiates
    CUSTOMER_PERSONA ||--o{ SESSION : participates
    
    SESSION ||--o{ MESSAGE : contains
    SESSION ||--o{ SESSION_STATE : has_state
    SESSION ||--o{ EVALUATION_LOG : generates
    SESSION ||--o{ STRATEGY_DECISION : produces
    SESSION ||--o{ ADOPTION_RECORD : tracks
    
    MESSAGE ||--o{ ADOPTION_RECORD : references
    STRATEGY_DECISION ||--o{ ADOPTION_RECORD : evaluates
    
    USER_STRATEGY_PROFILE ||--o{ CURRICULUM_PLAN : generates
    CURRICULUM_PLAN ||--o{ SESSION : recommends
```

### 5.2 核心数据表设计

#### 用户表 (users)
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'learner',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 会话表 (sessions)
```sql
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) REFERENCES organizations(id),
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    course_id VARCHAR(36) NOT NULL REFERENCES courses(id),
    scenario_id VARCHAR(36) NOT NULL REFERENCES scenario_configs(id),
    persona_id VARCHAR(36) NOT NULL REFERENCES customer_personas(id),
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL,
    total_turns INTEGER DEFAULT 0,
    total_duration_seconds INTEGER DEFAULT 0,
    final_score FLOAT,
    final_stage VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 消息表 (messages)
```sql
CREATE TABLE messages (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) REFERENCES organizations(id),
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id),
    turn_number INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    stage VARCHAR(50) NOT NULL,
    intent_result JSONB,
    npc_result JSONB,
    coach_result JSONB,
    evaluator_result JSONB,
    rag_result JSONB,
    compliance_result JSONB,
    turn_score FLOAT,
    dimension_scores JSONB,
    processing_time_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 能力采纳记录表 (adoption_records)
```sql
CREATE TABLE adoption_records (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id),
    turn_number INTEGER NOT NULL,
    advice_text TEXT NOT NULL,
    advice_type VARCHAR(50) NOT NULL,
    was_adopted BOOLEAN NOT NULL,
    adoption_evidence TEXT,
    skill_delta FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.3 数据存储策略

#### 5.3.1 主数据存储
- **SQLite** (MVP阶段)：单文件数据库，零配置，适合快速原型验证
- **PostgreSQL** (生产环境)：支持高并发、事务ACID、复杂查询优化

#### 5.3.2 缓存策略
```python
# Redis缓存层级
SESSION_CACHE_TTL = 3600      # 会话状态缓存1小时
USER_PROFILE_TTL = 7200       # 用户画像缓存2小时
SCENARIO_CONFIG_TTL = 86400   # 场景配置缓存24小时

# 缓存键命名规范
f"session:{session_id}:state"
f"user:{user_id}:profile"
f"scenario:{scenario_id}:config"
```

#### 5.3.3 数据同步机制
1. **读写分离**：查询操作优先使用缓存，写入操作直接更新数据库
2. **缓存失效**：采用Write-Through策略，保证数据一致性
3. **异步刷新**：后台任务定期同步缓存和数据库状态

### 5.4 数据备份和恢复

#### 5.4.1 备份策略
```bash
# 数据库备份脚本
#!/bin/bash
BACKUP_DIR="/backup/salesboost"
DATE=$(date +%Y%m%d_%H%M%S)

# SQLite备份
cp salesboost.db "$BACKUP_DIR/salesboost_$DATE.db"

# PostgreSQL备份（生产环境）
pg_dump -h localhost -U salesboost salesboost > "$BACKUP_DIR/salesboost_$DATE.sql"

# 向量数据库备份
cp -r chroma_db "$BACKUP_DIR/chroma_db_$DATE"
```

#### 5.4.2 恢复流程
1. **服务降级**：切换到只读模式，停止写入操作
2. **数据验证**：检查备份文件完整性和一致性
3. **数据恢复**：按备份时间顺序恢复数据
4. **服务验证**：验证系统功能完整性
5. **流量恢复**：逐步放开用户访问

## 6. 非功能性需求

### 6.1 性能优化方案

#### 6.1.1 响应时间优化
```python
# 异步并发处理
async def process_turn_concurrently(user_message: str) -> dict:
    # 并行执行多个Agent任务
    tasks = [
        intent_gate.process(user_message),
        npc_agent.generate_response(user_message),
        coach_agent.generate_advice(user_message),
        evaluator_agent.evaluate(user_message)
    ]
    
    # 并发执行，总时间 = 最慢的任务时间
    results = await asyncio.gather(*tasks)
    return aggregate_results(results)
```

#### 6.1.2 数据库优化
- **索引优化**：为高频查询字段建立复合索引
- **查询优化**：使用预加载减少N+1查询问题
- **连接池**：配置合理的数据库连接池参数

#### 6.1.3 缓存优化
```python
# 多级缓存架构
LOCAL_CACHE = {}      # 本地内存缓存（进程级）
REDIS_CACHE = redis   # 分布式缓存（服务级）
DB_CACHE = database   # 数据库缓存（存储级）

# 缓存穿透保护
async def get_with_cache_protection(key: str, fallback_func):
    # 布隆过滤器防止缓存穿透
    if not bloom_filter.might_contain(key):
        return None
    
    # 多级缓存查询
    value = LOCAL_CACHE.get(key) or await REDIS_CACHE.get(key)
    if value is None:
        value = await fallback_func()
        await set_cache(key, value)
    return value
```

### 6.2 高可用和容灾方案

#### 6.2.1 服务高可用
```yaml
# Docker Compose高可用配置
version: '3.8'
services:
  app:
    image: salesboost:latest
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 6.2.2 数据库高可用
```sql
-- PostgreSQL主从配置
-- 主库（读写）
primary_db:
  host: postgres-primary.internal
  port: 5432
  database: salesboost

-- 从库（只读）
replica_db:
  host: postgres-replica.internal
  port: 5432
  database: salesboost
  read_only: true
```

#### 6.2.3 容灾策略
1. **数据容灾**：跨可用区数据库备份
2. **服务容灾**：多可用区服务部署
3. **网络容灾**：CDN和负载均衡器配置
4. **故障切换**：自动故障检测和服务切换

### 6.3 监控和告警机制

#### 6.3.1 系统监控指标
```python
# 关键性能指标（KPI）
METRICS = {
    'request_latency': 'HTTP请求延迟',
    'websocket_connections': 'WebSocket连接数',
    'database_query_time': '数据库查询时间',
    'llm_response_time': 'LLM响应时间',
    'error_rate': '错误率',
    'session_completion_rate': '会话完成率',
    'user_adoption_rate': '能力采纳率'
}
```

#### 6.3.2 日志规范
```python
# 结构化日志格式
{
    "timestamp": "2024-01-19T10:30:00.123Z",
    "level": "INFO",
    "logger": "app.services.orchestrator",
    "message": "Turn processed successfully",
    "context": {
        "session_id": "uuid-v4",
        "user_id": "user-123",
        "turn_number": 5,
        "processing_time_ms": 1250,
        "score": 8.5
    },
    "request_id": "req-uuid-v4"
}
```

#### 6.3.3 告警规则
```yaml
# Prometheus告警规则
groups:
- name: salesboost_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "高错误率告警"
      description: "错误率超过10%，持续2分钟"
  
  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "高延迟告警"
      description: "95%分位延迟超过2秒，持续5分钟"
```

### 6.4 安全机制

#### 6.4.1 认证授权
```python
# JWT令牌结构
{
    "sub": "user-123",
    "org_id": "org-456",
    "role": "learner",
    "permissions": ["read:scenarios", "write:sessions"],
    "iat": 1705661400,
    "exp": 1705663200,
    "jti": "jwt-uuid-v4"
}
```

#### 6.4.2 输入验证
```python
# Pydantic模型验证
class UserMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    session_id: UUID4
    
    @validator('content')
    def validate_content(cls, v):
        # XSS防护
        v = html.escape(v.strip())
        # 敏感词过滤
        if contains_sensitive_words(v):
            raise ValueError('内容包含敏感词汇')
        return v
```

#### 6.4.3 限流控制
```python
# 基于令牌桶的限流算法
class TokenBucketRateLimiter:
    def __init__(self, rate: int, capacity: int):
        self.rate = rate          # 每秒生成令牌数
        self.capacity = capacity  # 桶容量
        self.tokens = capacity
        self.last_update = time.time()
    
    async def allow_request(self, user_id: str) -> bool:
        now = time.time()
        # 计算新增令牌
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        # 消费令牌
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

## 7. 部署架构

### 7.1 容器化部署
```dockerfile
# 多阶段构建Dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 生产环境架构
```yaml
# Kubernetes部署配置
apiVersion: apps/v1
kind: Deployment
metadata:
  name: salesboost-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: salesboost
  template:
    metadata:
      labels:
        app: salesboost
    spec:
      containers:
      - name: app
        image: salesboost:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: salesboost-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### 7.3 环境配置
```bash
# 生产环境环境变量
ENV_STATE=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@postgres:5432/salesboost
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-production-secret-key
OPENAI_API_KEY=your-openai-api-key
MAX_ACTIVE_SESSIONS=1000
SESSION_TIMEOUT_MINUTES=120
```

## 8. 总结

SalesBoost技术架构采用现代化的微服务设计理念，结合多智能体系统和实时通信技术，为销售培训提供了强大的技术支撑。架构设计充分考虑了从MVP到生产环境的平滑演进，通过合理的分层和模块化设计，确保系统的可扩展性、可维护性和高可用性。

关键设计决策：
1. **异步优先**：全面采用异步编程模型，支持高并发处理
2. **数据驱动**：以会话数据为核心，构建完整的学习闭环
3. **智能协同**：多Agent协同工作，提供个性化培训体验
4. **渐进演进**：从SQLite到PostgreSQL，从单体到微服务的演进路径
5. **安全可控**：多层次安全防护，确保系统稳定运行

该架构能够支撑SalesBoost平台的长期发展，为用户提供稳定、高效、智能的销售培训服务。