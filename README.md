# SalesBoost Backend

基于 **Clean Architecture + FastAPI + LangGraph** 的销售能力复制平台后端，实现了硅谷标准的 **"Hybrid Control FSM"**（混合控制状态机）：LLM 负责意图感知，Python 代码负责强制的状态流转。

## 🏗️ 架构特点

- **Clean Architecture**: 严格的关注点分离 (SoC)，模块化单体设计
- **Hybrid Control FSM**: LLM 意图感知 + Python 强制状态流转
- **12-Factor App**: 严格遵循云原生应用原则
- **Type Safety First**: mypy 严格模式，无 Any 类型，兼容 Python 3.8+
- **Async First**: 全异步架构，支持高并发
- **Error Resilience**: 完善的异常处理和降级策略
- **Code Quality**: 详细注释，数据结构优化，算法驱动

## 📁 Clean Architecture 项目结构

```
SalesBoost/
├── app/
│   ├── main.py                    # 🚪 入口文件 (仅 App 初始化)
│   ├── api/                       # 🌐 接口层 (Interface Layer)
│   │   ├── deps.py                # 🔗 依赖注入 (Dependencies)
│   │   └── endpoints/
│   │       └── websocket.py       # 📡 WS 路由 (Thin Layer)
│   ├── core/                      # ⚙️  核心基础设施
│   │   ├── config.py              # 🔧 Pydantic Settings (.env)
│   │   └── exceptions.py          # 🚨 自定义异常类
│   ├── schemas/                   # 📋 数据传输对象 (DTOs)
│   │   ├── state.py               # 🎯 Graph 状态 & Enums
│   │   └── protocol.py            # 📡 WebSocket 通信协议
│   ├── services/                  # 🧠 纯业务逻辑层
│   │   ├── fsm_service.py         # 🤖 状态机逻辑 (The Guard)
│   │   └── prompt_service.py      # 💬 提示词管理
│   └── agents/                    # 🎭 LangGraph 编排层
│       ├── nodes/                 # 🧩 解耦的节点逻辑
│       │   ├── npc.py             # 👤 NPC 响应节点
│       │   ├── coach.py           # 👨‍🏫 教练建议节点
│       │   └── router.py          # 🧭 路由决策节点
│       └── graph_builder.py       # 🏗️ 图构建与编译
├── .env.example                   # 📄 环境变量模板
├── requirements.txt               # 📦 依赖列表
├── run.py                         # 🚀 启动脚本
└── README.md                      # 📖 项目说明
```

## 🎯 销售阶段 (Sales Stages)

1. **OPENING** - 开场建立联系
2. **NEEDS_DISCOVERY** - 需求发现与挖掘
3. **PRODUCT_INTRO** - 产品介绍与演示
4. **OBJECTION_HANDLING** - 反对意见处理
5. **CLOSING** - 结单与成交

## 🚀 SaaS 升级 (v2.0.0)

2026 年最新架构，从 API 系统升级为可售卖的 SaaS 产品：

- **Multi-Tenancy**: 完整的租户隔离 (Tenant/User/Subscription)。
- **Admin Panel**: 可视化管理后台 (React + Shadcn UI)。
- **Knowledge Governance**: 知识库版本控制与回滚。
- **Production Ready WS**: 分布式 WebSocket，支持断线重连与 Redis 广播。
- **Silicon Valley Features**:
    - **Voice Interface**: ASR/TTS 语音链路。
    - **Persona Gen**: 一键生成客户人设。
    - **Live Copilot**: 实时辅助侧栏。

### 🔧 部署与迁移

#### 1. 数据库迁移
```bash
# 初始化数据库
python scripts/check_db_consistency.py

# 执行 Alembic 迁移
alembic upgrade head
```

#### 2. 本地双实例测试 (WebSocket)
为了验证 Redis 广播能力，可以启动两个不同端口的实例：
```bash
# Terminal 1
uvicorn app.main:app --port 8000

# Terminal 2
uvicorn app.main:app --port 8001
```
客户端连接任一端口，Redis 负责消息路由。

#### 3. 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 🔒 鉴权与租户
- **Admin**: 登录 `/admin` 管理后台，可管理所有租户。
- **Tenant Admin**: 登录后管理本租户的课程与学员。
- **Student**: 登录后进入 `/practice-room`。


```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，根据需要修改配置
```

### 4. 运行服务

```bash
python run.py
```

服务将在 `http://localhost:8000` 启动

### 5. 验证运行

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **WebSocket 连接**: ws://localhost:8000/ws/{session_id}

### 6. 测试 Hybrid Control FSM

打开 `test_client.html` 文件在浏览器中测试：

```bash
# 在浏览器中打开
start test_client.html
```

或直接在浏览器中打开 `file:///D:/SalesBoost/test_client.html`

**测试步骤**:
1. 等待连接建立 (显示 🟢 已连接)
2. 输入销售话术并发送
3. 观察 NPC 客户响应 (左侧对话框)
4. 查看教练实时洞察 (右侧面板)
5. 测试状态转换 (多轮对话后自动进入下一阶段)

## 🔧 Hybrid Control FSM 详解

## 🤖 AI 核心升级

### LLM 集成架构

SalesBoost 现已完全集成真实 LLM，支持：

- **ChatOpenAI**: 兼容 OpenAI GPT 和 DeepSeek
- **结构化输出**: Coach 节点强制 JSON 输出格式
- **双温度配置**: NPC (0.7) 增加多样性，Coach (0.2) 保证严谨性
- **异常处理**: LLM 调用失败时自动降级到 Mock 模式

### 配置 LLM

在 `.env` 文件中设置：

```env
# OpenAI 配置
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1  # 或 DeepSeek URL
```

### 高构念提示词

- **NPC System Prompt**: 模拟刁钻客户行为，基于情绪动态响应
- **Coach System Prompt**: 专业销售教练，提供结构化指导建议

### 核心理念
- **LLM 负责意图感知**: 智能理解用户输入，提取语义信息
- **Python 代码强制状态流转**: 确保业务规则的确定性和可预测性

### 状态转换规则 (The Guard)

| 从状态 | 到状态 | 触发条件 | 理由 |
|--------|--------|----------|------|
| OPENING | NEEDS_DISCOVERY | 对话轮数 > 2 | 建立基础联系后开始挖掘需求 |
| NEEDS_DISCOVERY | PRODUCT_INTRO | 检测产品关键词 | 用户表现出产品兴趣 |
| PRODUCT_INTRO | OBJECTION_HANDLING | 检测反对关键词 | 需要处理疑虑和反对意见 |
| OBJECTION_HANDLING | CLOSING | 反对意见解决 | 进入最终成交阶段 |
| CLOSING | - | - | 最终状态，保持不变 |

## API 接口

### WebSocket 端点

- **URL**: `/ws/{session_id}`
- **协议**: 自定义协议，包含 `channel` 字段

#### 支持的频道类型
- `NPC`: 模拟客户消息
- `COACH`: 教练建议
- `SYSTEM`: 系统消息

### REST API 端点

- `GET /`: 根路径
- `GET /health`: 健康检查
- `GET /sessions/{session_id}/state`: 获取会话状态

## 状态机逻辑

### 自动状态转换规则

- **OPENING → NEEDS_DISCOVERY**: 当对话轮数 > 2 时自动转换
- **NEEDS_DISCOVERY → PRODUCT_INTRO**: 检测到产品相关关键词
- **PRODUCT_INTRO → OBJECTION_HANDLING**: 检测到反对意见关键词
- **OBJECTION_HANDLING → CLOSING**: 反对意见处理完成后

### NPC 情绪系统

- 情绪值范围: 0.0 - 1.0
- 根据用户消息内容动态调整情绪
- 影响教练建议的内容

## 🎭 Mock 策略 (Stage 1)

当前实现 **Mock 优先策略**，可立即运行测试，无需 API 密钥：

### Mock 节点实现

- **`npc.py`**: `mock_npc_response()` - 模拟客户对话响应
- **`coach.py`**: `mock_coach_insight()` - 模拟教练建议（JSON 格式）
- **`router.py`**: 基于规则的路由决策

### 异步延迟模拟

每个 Mock 节点都包含 `asyncio.sleep(1)` 来模拟真实的 LLM 处理延迟。

### 替换为真实 LLM (Stage 2)

在各个节点文件中找到 `TODO` 注释，替换为真实的 OpenAI API 调用：

```python
# TODO: Replace with real LLM call
# 在 npc.py 中：
response = await self._call_openai_api(prompt)

# 在 coach.py 中：
insight = await self._call_openai_api(prompt)
```

## 🛠️ 开发指南

### 🆕 添加新的销售阶段

1. **Schema 层**: 在 `app/schemas/state.py` 的 `SalesStage` 枚举中添加新阶段
2. **业务逻辑层**: 在 `app/services/fsm_service.py` 中更新转换规则
3. **提示词层**: 在 `app/services/prompt_service.py` 中添加对应模板
4. **节点层**: 在 `app/agents/nodes/` 中添加 Mock 响应逻辑

### 📡 扩展通信协议

1. **Schema 层**: 在 `app/schemas/protocol.py` 中添加新的消息类型
2. **更新映射**: 在 `MESSAGE_TYPE_MAP` 中注册新类型
3. **API 层**: 在 `app/api/endpoints/websocket.py` 中添加处理逻辑

### 🔧 添加新的节点类型

1. **创建节点**: 在 `app/agents/nodes/` 中创建新节点类
2. **实现接口**: 继承并实现 `__call__` 方法，返回 `AgentOutput`
3. **注册节点**: 在 `app/agents/graph_builder.py` 中添加节点实例
4. **更新路由**: 在 `RouterNode` 中添加决策逻辑

### 🧪 测试策略

```bash
# 类型检查 (推荐)
mypy app/ --strict

# 代码格式化
black app/
isort app/

# 运行测试 (未来扩展)
pytest tests/
```

## ⚙️ 环境变量配置

复制 `.env.example` 为 `.env` 并根据需要修改：

```env
# 项目基本信息
PROJECT_NAME=SalesBoost
VERSION=1.0.0
DESCRIPTION=基于 Multi-Agent 的销售能力复制平台

# 环境配置
ENV_STATE=development  # development | production | testing
DEBUG=true

# 服务器配置
HOST=0.0.0.0
PORT=8000

# CORS 配置 (生产环境请设置具体域名)
CORS_ORIGINS=*

# OpenAI 配置 (目前可选，用于未来替换 Mock)
# OPENAI_API_KEY=your_openai_api_key_here
# OPENAI_MODEL=gpt-4

# FSM 配置
FSM_OPENING_TO_DISCOVERY_TURN_THRESHOLD=2

# WebSocket 配置
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_PING_TIMEOUT=10

# 会话管理
SESSION_TIMEOUT_MINUTES=60
MAX_ACTIVE_SESSIONS=100

# 日志配置
LOG_LEVEL=INFO
```

## 🛡️ 架构原则遵循

### Clean Architecture
- ✅ **关注点分离**: 严格的层级划分，无循环依赖
- ✅ **依赖倒置**: 高层模块不依赖低层模块
- ✅ **单一职责**: 每个模块职责明确

### 12-Factor App
- ✅ **配置管理**: 环境变量管理配置
- ✅ **依赖声明**: 明确声明依赖关系
- ✅ **无状态进程**: 无本地状态存储
- ✅ **并发模型**: 异步处理支持高并发

### Type Safety
- ✅ **mypy 严格模式**: 无 `Any` 类型使用
- ✅ **Pydantic v2**: 强类型数据验证
- ✅ **StrEnum**: Python 3.11+ 枚举类型

## 🧪 快速测试指南

### 启动后端服务

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python run.py
```

### 运行可视化测试

```bash
# 方法1: 在浏览器中打开HTML文件
start test_client.html

# 方法2: 使用Python启动本地服务器
python -m http.server 8080
# 然后访问: http://localhost:8080/test_client.html
```

### 运行集成测试

```bash
# 基础功能集成测试
python test_integration.py

# LLM 集成专项测试
python test_llm_integration.py
```

### 测试要点

1. **连接建立**: WebSocket 连接成功显示 "🟢 已连接"
2. **消息收发**: 发送销售话术，接收 NPC 和教练响应
3. **状态转换**: 多轮对话后观察阶段自动转换
4. **实时洞察**: 右侧面板显示教练建议和分析

## 🏆 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **Web Framework** | FastAPI + Uvicorn | 异步 Web 框架，支持 WebSocket |
| **Configuration** | pydantic-settings | 12-Factor 配置管理 |
| **Data Validation** | Pydantic v2 | 强类型数据模型 |
| **State Management** | TypedDict + StrEnum | 类型安全的状态定义 |
| **Business Logic** | Pure Python Classes | 纯业务逻辑，无框架依赖 |
| **Agent Orchestration** | Custom Graph Builder | LangGraph 风格的编排 |
| **Communication** | WebSocket Protocol | 自定义协议，支持多频道 |
| **Testing** | HTML Client + Integration Tests | 可视化测试和自动化验证 |

## 🎮 销售任务模拟平台（Sales Simulation）

SalesBoost 内置了一个**子系统级多智能体销售任务模拟平台**，用于：

- 🔬 构建可复现的销售任务模拟环境
- 🤖 支持单/多智能体长周期任务运行
- 📊 生成轨迹数据与稳定性评估报告
- 🎯 自动生成 Post-training 偏好数据（SFT/DPO/GRPO）

### 快速开始

#### CLI 方式运行

```bash
# 运行单个场景（单智能体）
python -m app.sales_simulation.cli run \
  --scenario scenario_001 \
  --agent-type single \
  --num-runs 10

# 运行多智能体协作
python -m app.sales_simulation.cli run \
  --scenario scenario_002 \
  --agent-type multi \
  --num-runs 5

# 列出所有场景
python -m app.sales_simulation.cli list
```

#### API 方式运行

```bash
# 启动模拟任务
curl -X POST http://localhost:8000/api/v1/sales-sim/run/ \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "scenario_001",
    "agent_type": "single",
    "num_trajectories": 10,
    "seed": 42
  }'

# 查询评估结果
curl http://localhost:8000/api/v1/sales-sim/eval/{run_id}
```

### 详细文档

参见 `app/sales_simulation/README.md`

---

## 📋 许可证

本项目采用 MIT 许可证。
