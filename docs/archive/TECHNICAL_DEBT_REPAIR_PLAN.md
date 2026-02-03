# 🔧 关键技术债务修复计划

**规划日期**: 2026-01-31
**项目**: SalesBoost
**当前完成度**: 95%
**目标**: 提升至98%生产级标准

---

## 📊 技术债务优先级矩阵

| 优先级 | 债务项 | 影响范围 | 修复难度 | 预期收益 |
|--------|--------|----------|----------|----------|
| P0 | 移除遗留协调器代码 | 高 | 中 | 代码简化30% |
| P0 | 数据库迁移至PostgreSQL | 高 | 高 | 生产可扩展性 |
| P1 | 前端硬编码数据替换 | 中 | 低 | 用户体验提升 |
| P1 | 配置系统重构 | 中 | 中 | 可维护性提升 |
| P2 | Docker镜像优化 | 低 | 中 | 构建速度提升50% |
| P2 | 测试覆盖率提升 | 中 | 高 | 代码质量保障 |

---

## 🎯 P0级别：关键技术债务

### 1. 移除遗留协调器代码

**问题描述**:
- `app/engine/coordinator/workflow_coordinator.py` (已删除但仍有引用)
- `app/engine/intent/intent_classifier.py` (已删除但仍有引用)
- `LangGraphCoordinator` 和 `WorkflowCoordinator` 的向后兼容代码增加了 `ProductionCoordinator` 的复杂度

**影响**:
- 代码库维护成本高
- 新开发者理解困难
- 潜在的bug风险

**修复方案**:

#### 1.1 清理已删除文件的引用
```bash
# 搜索所有引用
grep -r "workflow_coordinator" --include="*.py"
grep -r "intent_classifier" --include="*.py"
```

**需要修改的文件**:
- `app/engine/coordinator/__init__.py` - 移除导入
- `app/engine/coordinator/production_coordinator.py` - 移除fallback逻辑
- `tests/` - 更新测试用例

#### 1.2 简化ProductionCoordinator
**位置**: `app/engine/coordinator/production_coordinator.py`

**当前问题**:
```python
# 支持多种协调器的fallback逻辑
if workflow_type == "dynamic":
    result = await self.dynamic_workflow.execute(...)
elif workflow_type == "langgraph":  # 遗留
    result = await self.langgraph_coordinator.execute(...)
elif workflow_type == "legacy":  # 遗留
    result = await self.workflow_coordinator.execute(...)
```

**目标状态**:
```python
# 只保留dynamic_workflow
result = await self.dynamic_workflow.execute(...)
```

**修复步骤**:
1. 确认所有生产流量都使用 `dynamic_workflow`
2. 移除 `langgraph_coordinator` 和 `workflow_coordinator` 的初始化
3. 删除相关的fallback逻辑
4. 更新配置文件，移除 `workflow_type` 选项
5. 更新文档

**预期收益**:
- 代码行数减少 ~200行
- 维护成本降低 30%
- 新开发者上手时间减少 50%

---

### 2. 数据库迁移至PostgreSQL

**问题描述**:
- 当前使用SQLite + WAL模式
- 生产环境需要更强的并发支持
- 审计报告建议迁移到PostgreSQL

**影响**:
- 并发会话数限制在100以内
- 无法实现真正的水平扩展
- 数据一致性风险

**修复方案**:

#### 2.1 PostgreSQL配置
**位置**: `core/config.py`

**当前配置**:
```python
DATABASE_URL: str = "sqlite+aiosqlite:///./salesboost.db"
```

**目标配置**:
```python
DATABASE_URL: str = Field(
    default="postgresql+asyncpg://user:pass@localhost:5432/salesboost",
    env="DATABASE_URL"
)
```

#### 2.2 迁移步骤

**阶段1: 准备工作 (1天)**
1. 安装PostgreSQL依赖
```bash
pip install asyncpg psycopg2-binary
```

2. 更新 `requirements.txt`
```txt
asyncpg==0.29.0
psycopg2-binary==2.9.9
```

3. 创建PostgreSQL数据库
```sql
CREATE DATABASE salesboost;
CREATE USER salesboost_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE salesboost TO salesboost_user;
```

**阶段2: 代码适配 (2天)**
1. 更新数据库连接代码
   - `core/database.py` - 修改连接字符串处理
   - `alembic/env.py` - 更新迁移配置

2. 修复SQLite特定语法
   - 替换 `AUTOINCREMENT` 为 `SERIAL`
   - 替换 `DATETIME` 为 `TIMESTAMP`
   - 修复JSON字段处理

3. 更新Alembic迁移脚本
```python
# 检查并修复所有迁移脚本
alembic history
alembic check
```

**阶段3: 数据迁移 (1天)**
1. 导出SQLite数据
```bash
python scripts/db/export_sqlite_data.py
```

2. 导入PostgreSQL
```bash
python scripts/db/import_to_postgres.py
```

3. 验证数据完整性
```bash
python scripts/db/verify_migration.py
```

**阶段4: 测试验证 (2天)**
1. 运行所有单元测试
2. 运行集成测试
3. 性能基准测试
4. 并发压力测试

**阶段5: 生产部署 (1天)**
1. 更新 `docker-compose.yml`
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: salesboost
      POSTGRES_USER: salesboost_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

2. 更新 `.env.example`
```bash
DATABASE_URL=postgresql+asyncpg://salesboost_user:password@postgres:5432/salesboost
```

3. 更新部署文档

**预期收益**:
- 并发支持提升至 1000+ 会话
- 支持真正的水平扩展
- 数据一致性保障
- 生产级可靠性

**风险控制**:
- 保留SQLite作为开发环境选项
- 提供回滚方案
- 完整的数据备份

---

## 🔥 P1级别：重要技术债务

### 3. 前端硬编码数据替换

**问题描述**:
- `frontend/src/pages/student/Evaluation.tsx:74` - 硬编码随机分数
- 其他页面可能存在类似问题

**影响**:
- 用户看到的数据不真实
- 影响产品可信度

**修复方案**:

#### 3.1 识别所有硬编码数据
```bash
# 搜索TODO和硬编码模式
cd frontend
grep -r "TODO" src/
grep -r "Math.random" src/
grep -r "mock" src/ -i
```

#### 3.2 修复Evaluation.tsx
**位置**: `frontend/src/pages/student/Evaluation.tsx:74`

**当前代码**:
```typescript
// TODO: Replace with real data
const score = Math.floor(Math.random() * 100);
```

**修复方案**:
```typescript
// 从API获取真实评估数据
const { data: evaluation } = useQuery({
  queryKey: ['evaluation', sessionId],
  queryFn: () => api.get(`/api/v1/evaluations/${sessionId}`)
});

const score = evaluation?.overall_score ?? 0;
```

#### 3.3 创建API端点
**位置**: `api/endpoints/evaluations.py` (新建)

```python
@router.get("/evaluations/{session_id}")
async def get_evaluation(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取会话评估结果"""
    evaluation = await db.execute(
        select(Evaluation).where(Evaluation.session_id == session_id)
    )
    return evaluation.scalar_one_or_none()
```

**修复步骤**:
1. 创建评估API端点
2. 更新前端数据获取逻辑
3. 添加加载状态和错误处理
4. 更新测试用例

**预期收益**:
- 用户看到真实数据
- 提升产品可信度
- 完善数据流

---

### 4. 配置系统重构

**问题描述**:
- `core/config.py` 的 `Settings` 类过大 (200+ 行)
- 配置项混杂，难以维护

**影响**:
- 配置管理混乱
- 模块间耦合度高
- 难以进行模块化部署

**修复方案**:

#### 4.1 拆分配置模块

**目标结构**:
```
core/
├── config/
│   ├── __init__.py
│   ├── base.py          # 基础配置
│   ├── database.py      # 数据库配置
│   ├── llm.py           # LLM配置
│   ├── monitoring.py    # 监控配置
│   ├── security.py      # 安全配置
│   └── feature_flags.py # 特性开关
```

**实现示例**:

**base.py**:
```python
from pydantic_settings import BaseSettings

class BaseConfig(BaseSettings):
    """基础配置"""
    APP_NAME: str = "SalesBoost"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
```

**database.py**:
```python
class DatabaseConfig(BaseSettings):
    """数据库配置"""
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"
    QDRANT_URL: str = "http://localhost:6333"
```

**llm.py**:
```python
class LLMConfig(BaseSettings):
    """LLM配置"""
    SILICONFLOW_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None

    DEFAULT_MODEL: str = "deepseek-chat"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
```

**统一配置入口** (`core/config/__init__.py`):
```python
from .base import BaseConfig
from .database import DatabaseConfig
from .llm import LLMConfig
from .monitoring import MonitoringConfig
from .security import SecurityConfig

class Settings(BaseConfig, DatabaseConfig, LLMConfig, MonitoringConfig, SecurityConfig):
    """统一配置类"""
    pass

settings = Settings()
```

**修复步骤**:
1. 创建配置模块目录结构
2. 按功能拆分配置类
3. 更新所有导入语句
4. 更新测试用例
5. 更新文档

**预期收益**:
- 配置管理清晰
- 模块化程度提升
- 易于维护和扩展

---

## ⚡ P2级别：优化项

### 5. Docker镜像优化

**问题描述**:
- 镜像构建时间长 (10+ 分钟)
- 镜像体积大 (2GB+)
- 重型依赖拖慢部署

**影响**:
- 开发迭代速度慢
- CI/CD流水线耗时长
- 部署成本高

**修复方案**:

#### 5.1 多阶段构建

**当前Dockerfile**:
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app"]
```

**优化后Dockerfile**:
```dockerfile
# 阶段1: 构建依赖
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 阶段2: 运行时镜像
FROM python:3.11-slim
WORKDIR /app

# 只复制必要的依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 5.2 依赖分层

**创建多个requirements文件**:

**requirements-base.txt** (核心依赖):
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
sqlalchemy[asyncio]==2.0.25
```

**requirements-ai.txt** (AI依赖):
```txt
langchain==0.1.0
openai==1.10.0
anthropic==0.8.1
```

**requirements-heavy.txt** (重型依赖):
```txt
torch==2.1.2
paddleocr==2.7.0
pyannote.audio==3.1.1
```

**Dockerfile.production**:
```dockerfile
# 基础镜像
FROM python:3.11-slim as base
RUN pip install --no-cache-dir -r requirements-base.txt

# AI镜像
FROM base as ai
RUN pip install --no-cache-dir -r requirements-ai.txt

# 完整镜像 (可选)
FROM ai as full
RUN pip install --no-cache-dir -r requirements-heavy.txt
```

#### 5.3 预构建基础镜像

**创建基础镜像**:
```bash
# 构建并推送基础镜像
docker build -t salesboost-base:latest -f Dockerfile.base .
docker push salesboost-base:latest
```

**使用基础镜像**:
```dockerfile
FROM salesboost-base:latest
COPY . .
CMD ["uvicorn", "main:app"]
```

**预期收益**:
- 构建时间减少 50% (10分钟 → 5分钟)
- 镜像体积减少 30% (2GB → 1.4GB)
- CI/CD速度提升

---

### 6. 测试覆盖率提升

**问题描述**:
- 当前集成测试覆盖率 ~60%
- 缺少边界条件测试
- 缺少端到端测试

**影响**:
- 代码质量风险
- 重构困难
- 生产bug风险

**修复方案**:

#### 6.1 测试覆盖率目标

| 测试类型 | 当前覆盖率 | 目标覆盖率 | 优先级 |
|---------|-----------|-----------|--------|
| 单元测试 | 70% | 85% | P1 |
| 集成测试 | 60% | 80% | P0 |
| E2E测试 | 30% | 70% | P1 |
| 性能测试 | 40% | 60% | P2 |

#### 6.2 关键测试用例补充

**需要补充的测试**:

1. **协调器测试** (`tests/unit/test_production_coordinator.py`)
```python
@pytest.mark.asyncio
async def test_coordinator_fallback():
    """测试协调器降级逻辑"""
    # 模拟LLM失败
    # 验证fallback到mock响应
    pass

@pytest.mark.asyncio
async def test_coordinator_concurrent_sessions():
    """测试并发会话处理"""
    # 创建100个并发会话
    # 验证无资源泄漏
    pass
```

2. **RAG系统测试** (`tests/integration/test_rag_system.py`)
```python
@pytest.mark.asyncio
async def test_hybrid_search():
    """测试混合检索"""
    # 测试向量搜索 + BM25
    # 验证重排序效果
    pass

@pytest.mark.asyncio
async def test_self_rag_reflection():
    """测试Self-RAG反思循环"""
    # 验证相关性检查
    # 验证忠实度检查
    pass
```

3. **WebSocket测试** (`tests/integration/test_websocket.py`)
```python
@pytest.mark.asyncio
async def test_websocket_reconnection():
    """测试WebSocket重连"""
    # 模拟连接断开
    # 验证自动重连
    pass

@pytest.mark.asyncio
async def test_websocket_message_ordering():
    """测试消息顺序"""
    # 发送多条消息
    # 验证接收顺序正确
    pass
```

4. **前端E2E测试** (`frontend/e2e/evaluation.spec.ts`)
```typescript
test('完整评估流程', async ({ page }) => {
  // 登录
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.fill('[name="password"]', 'password');
  await page.click('button[type="submit"]');

  // 开始模拟
  await page.goto('/student/evaluation');
  await page.click('button:has-text("开始模拟")');

  // 发送消息
  await page.fill('[name="message"]', '你好，我想了解产品');
  await page.click('button:has-text("发送")');

  // 验证响应
  await expect(page.locator('.coach-message')).toBeVisible();

  // 结束会话
  await page.click('button:has-text("结束")');

  // 验证评估报告
  await expect(page.locator('.evaluation-report')).toBeVisible();
});
```

#### 6.3 测试基础设施

**配置pytest-cov**:
```ini
# pytest.ini
[pytest]
addopts =
    --cov=app
    --cov=api
    --cov=core
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

**配置Playwright**:
```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
});
```

**预期收益**:
- 代码质量提升
- 重构信心增强
- 生产bug减少 50%

---

## 📋 实施计划

### 时间线

| 阶段 | 任务 | 工作量 | 依赖 |
|------|------|--------|------|
| 第1周 | P0-1: 移除遗留代码 | 3天 | 无 |
| 第1-2周 | P0-2: PostgreSQL迁移 | 7天 | 无 |
| 第2周 | P1-3: 前端硬编码修复 | 2天 | 无 |
| 第3周 | P1-4: 配置系统重构 | 3天 | P0-1 |
| 第3周 | P2-5: Docker优化 | 2天 | 无 |
| 第4周 | P2-6: 测试覆盖率提升 | 5天 | P0-1, P0-2 |

**总工作量**: 22天 (约1个月)

### 资源需求

- **开发人员**: 2人
- **测试人员**: 1人
- **DevOps**: 0.5人

### 风险控制

1. **数据库迁移风险**
   - 完整数据备份
   - 灰度迁移方案
   - 回滚预案

2. **代码重构风险**
   - 充分的测试覆盖
   - 代码审查
   - 分支保护

3. **性能回归风险**
   - 性能基准测试
   - 持续监控
   - 告警机制

---

## ✅ 验收标准

### P0级别
- [ ] 所有遗留代码引用已清理
- [ ] PostgreSQL迁移完成，所有测试通过
- [ ] 生产环境支持1000+并发会话

### P1级别
- [ ] 前端无硬编码数据
- [ ] 配置系统模块化，易于维护
- [ ] 代码审查通过

### P2级别
- [ ] Docker构建时间 < 5分钟
- [ ] 镜像体积 < 1.5GB
- [ ] 测试覆盖率 > 80%

---

## 📊 成功指标

| 指标 | 当前值 | 目标值 | 测量方法 |
|------|--------|--------|----------|
| 代码复杂度 | 中 | 低 | SonarQube |
| 技术债务时间 | 15天 | 5天 | SonarQube |
| 测试覆盖率 | 60% | 80% | pytest-cov |
| 构建时间 | 10分钟 | 5分钟 | CI/CD日志 |
| 并发支持 | 100 | 1000+ | 压力测试 |

---

**规划完成日期**: 2026-01-31
**规划人员**: Claude Sonnet 4.5
**下一步**: 开始P0级别任务实施
