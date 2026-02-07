# 项目结构迁移指南

## 概述

SalesBoost 项目已经按照世界级开源项目标准进行了重组。本指南将帮助您了解新的项目结构并更新您的本地开发环境。

---

## 主要变更

### 1. 后端代码移动到 `backend/` 目录

**之前：**
```
SalesBoost/
├── main.py
├── app/
├── core/
├── api/
├── schemas/
├── tests/
├── scripts/
├── alembic/
└── config/
```

**之后：**
```
SalesBoost/
└── backend/
    ├── main.py
    ├── requirements.txt
    ├── pytest.ini
    ├── app/
    │   ├── core/
    │   ├── api/
    │   ├── schemas/
    │   ├── agents/
    │   ├── services/
    │   ├── engine/
    │   └── infra/
    ├── tests/
    ├── scripts/
    ├── alembic/
    └── config/
```

### 2. 部署配置整合到 `deployment/` 目录

**之前：**
- `docker-compose.yml` (根目录)
- `deploy.sh` (根目录)
- `deployment/` (部分配置)
- `deploy/` (重复目录)
- `deploy-scripts/` (重复目录)

**之后：**
```
deployment/
├── docker/
│   ├── compose.base.yml
│   ├── compose.dev.yml
│   ├── compose.prod.yml
│   └── compose.monitoring.yml
├── scripts/
│   ├── deploy-local.sh
│   ├── deploy-production.sh
│   ├── deploy-cloud-aliyun.sh
│   └── deploy-cloud-railway.sh
├── kubernetes/
├── cloud/
└── monitoring/
    ├── grafana/
    └── prometheus/
```

### 3. 使用相对导入替代绝对导入

**之前：**
```python
from app.agents.coach import CoachAgent
from core.config import settings
from api.endpoints.sessions import router
```

**之后：**
```python
# 在 backend/app/ 内的文件中
from .agents.coach import CoachAgent
from .core.config import settings
from .api.endpoints.sessions import router

# 在 backend/main.py 中
from backend.app.agents.coach import CoachAgent
from backend.app.core.config import settings
```

### 4. 清理根目录

**删除的文件/目录：**
- `temp-student-persona.html` → 移动到 `frontend/public/generated/`
- `temp-student-tasks.html` → 移动到 `frontend/public/generated/`
- `webapp-index.html` → 移动到 `frontend/public/`
- `generate_pages.py` → 移动到 `backend/scripts/generation/`
- `deploy/` → 删除（已整合）
- `deploy-scripts/` → 删除（已整合）
- `deploy-package/` → 删除（已整合）

**新增的文件：**
- `Makefile` - 常用命令快捷方式
- `scripts/setup.sh` - 项目设置脚本
- `scripts/dev.sh` - 开发环境启动脚本

---

## 开发者需要做的事

### 1. 更新本地环境

```bash
# 拉取最新代码
git checkout main
git pull origin main

# 重新安装依赖
cd backend
pip install -r requirements.txt

cd ../frontend
npm install
```

### 2. 更新 IDE 配置

#### VS Code

更新 `.vscode/settings.json`：

```json
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/backend"
  ],
  "python.autoComplete.extraPaths": [
    "${workspaceFolder}/backend"
  ]
}
```

#### PyCharm

1. 打开项目设置 (File → Settings)
2. 进入 Project → Project Structure
3. 将 `backend/` 标记为 "Sources Root"
4. 将 `backend/app/` 标记为 "Sources Root"

### 3. 更新环境变量

```bash
# 复制环境变量模板
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 编辑 .env 文件，填入您的配置
```

### 4. 使用新的开发命令

#### 使用 Makefile（推荐）

```bash
# 查看所有可用命令
make help

# 初始设置
make setup

# 启动开发环境
make dev

# 运行测试
make test

# 代码检查
make lint

# 格式化代码
make format

# 构建生产镜像
make build
```

#### 使用脚本

```bash
# 初始设置
./scripts/setup.sh

# 启动开发环境
./scripts/dev.sh
```

#### 手动启动

```bash
# 启动 Docker 服务
docker-compose -f deployment/docker/compose.base.yml -f deployment/docker/compose.dev.yml up -d

# 启动后端
cd backend
python main.py

# 启动前端（新终端）
cd frontend
npm run dev
```

---

## 常见问题

### Q: 导入错误 "ModuleNotFoundError: No module named 'app'"

**A:** 这是因为代码已经更新为使用相对导入。确保：
1. 您在 `backend/` 目录下运行 Python 代码
2. 使用相对导入 `from .app` 而不是 `from app`
3. 在 `backend/main.py` 中使用 `from backend.app` 导入

### Q: Docker 构建失败

**A:** 检查以下几点：
1. Dockerfile 中的路径是否更新为 `backend/`
2. docker-compose 文件是否使用新路径：`deployment/docker/compose.base.yml`
3. 运行 `make clean` 清理旧的构建缓存

### Q: 部署脚本找不到

**A:** 所有部署脚本现在在 `deployment/scripts/` 目录：
```bash
# 本地部署
./deployment/scripts/deploy-local.sh

# 生产部署
./deployment/scripts/deploy-production.sh

# 云部署
./deployment/scripts/deploy-cloud-aliyun.sh
```

### Q: 测试失败

**A:** 确保：
1. 在 `backend/` 目录下运行测试：`cd backend && pytest tests/`
2. 或使用 Makefile：`make test`
3. 检查 `backend/pytest.ini` 配置是否正确

### Q: 前端无法连接后端

**A:** 检查：
1. 后端是否在运行（http://localhost:8000）
2. 前端环境变量中的 API URL 是否正确
3. CORS 配置是否正确

### Q: Git 历史记录丢失

**A:** 我们创建了备份分支 `backup/before-restructure`，您可以随时查看：
```bash
git checkout backup/before-restructure
```

---

## 新项目结构详解

### 根目录

```
SalesBoost/
├── README.md                    # 项目概览
├── LICENSE                      # MIT 许可证
├── CONTRIBUTING.md              # 贡献指南
├── CHANGELOG.md                # 版本历史
├── Makefile                    # 常用命令
├── .gitignore                  # Git 忽略规则
├── .env.example                # 环境变量模板
├── Dockerfile.backend          # 后端 Docker 镜像
├── Dockerfile.frontend         # 前端 Docker 镜像
│
├── backend/                    # 后端应用
├── frontend/                   # 前端应用
├── deployment/                 # 部署配置
├── scripts/                    # 工具脚本
├── docs/                       # 文档
├── data/                       # 数据文件
├── models/                     # ML 模型
└── storage/                    # 运行时数据
```

### Backend 目录

```
backend/
├── main.py                     # FastAPI 应用入口
├── requirements.txt            # Python 依赖
├── pytest.ini                  # 测试配置
│
├── app/                        # 应用代码
│   ├── core/                   # 核心基础设施
│   ├── api/                    # API 层
│   ├── agents/                 # AI 智能体
│   ├── services/               # 业务逻辑
│   ├── models/                 # 数据模型
│   ├── schemas/                # Pydantic 模式
│   ├── tools/                  # 智能体工具
│   ├── memory/                 # 记忆系统
│   ├── retrieval/              # RAG/知识检索
│   ├── engine/                 # 工作流引擎
│   └── infra/                  # 基础设施
│
├── tests/                      # 测试套件
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   ├── e2e/                    # 端到端测试
│   └── performance/            # 性能测试
│
├── scripts/                    # 工具脚本
│   ├── db/                     # 数据库脚本
│   ├── data/                   # 数据处理
│   └── generation/             # 代码生成
│
├── alembic/                    # 数据库迁移
└── config/                     # 配置文件
```

### Deployment 目录

```
deployment/
├── docker/                     # Docker 配置
│   ├── compose.base.yml        # 基础服务
│   ├── compose.dev.yml         # 开发覆盖
│   ├── compose.prod.yml        # 生产覆盖
│   └── compose.monitoring.yml  # 监控栈
│
├── scripts/                    # 部署脚本
│   ├── deploy-local.sh         # 本地部署
│   ├── deploy-production.sh    # 生产部署
│   ├── deploy-cloud-aliyun.sh  # 阿里云部署
│   └── deploy-cloud-railway.sh # Railway 部署
│
├── kubernetes/                 # K8s 配置
├── cloud/                      # 云平台配置
└── monitoring/                 # 监控配置
    ├── grafana/                # Grafana 仪表板
    └── prometheus/             # Prometheus 配置
```

---

## 迁移检查清单

### 环境设置
- [ ] 拉取最新代码
- [ ] 安装后端依赖 (`cd backend && pip install -r requirements.txt`)
- [ ] 安装前端依赖 (`cd frontend && npm install`)
- [ ] 复制并配置 .env 文件
- [ ] 更新 IDE 配置

### 代码更新
- [ ] 理解新的导入路径（相对导入）
- [ ] 如果有自定义代码，更新导入语句
- [ ] 运行测试确保一切正常

### 开发流程
- [ ] 学习使用 Makefile 命令
- [ ] 测试启动开发环境 (`make dev`)
- [ ] 验证后端 API (http://localhost:8000/docs)
- [ ] 验证前端应用 (http://localhost:5173)

### 部署流程
- [ ] 了解新的部署脚本位置
- [ ] 更新 CI/CD 配置（如果有）
- [ ] 测试本地部署流程

---

## 获取帮助

如果您遇到任何问题：

1. **查看文档**：`docs/` 目录包含详细文档
2. **运行帮助命令**：`make help` 查看所有可用命令
3. **检查日志**：`make docker-logs` 查看服务日志
4. **查看状态**：`make status` 查看项目状态
5. **联系团队**：在团队频道提问

---

## 收益

这次重组带来的好处：

### ✅ 更清晰的结构
- 后端、前端、部署配置清晰分离
- 符合行业最佳实践
- 新开发者更容易理解

### ✅ 更好的开发体验
- Makefile 简化常用操作
- 相对导入更易维护
- 更好的 IDE 支持

### ✅ 更可靠的部署
- 统一的部署脚本
- 清晰的环境配置
- 更好的监控集成

### ✅ 更易协作
- 标准化的项目结构
- 减少合并冲突
- 更容易代码审查

---

## 下一步

1. 完成本地环境更新
2. 熟悉新的开发命令
3. 阅读更新后的文档
4. 开始使用新结构进行开发

欢迎来到新的 SalesBoost 项目结构！🎉
