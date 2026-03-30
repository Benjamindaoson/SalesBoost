# SalesBoost 完整文件清单

**生成时间**: 2026-02-22  
**排除**: node_modules, .git, __pycache__, .pytest_cache, dist, build, *.pyc

---

## 根目录

| 文件/文件夹 | 类型 |
|-------------|------|
| .env.example | 配置 |
| .gitignore | 配置 |
| .github/workflows/ci.yml | CI |
| .github/workflows/ci-cd.yml | CI |
| IMPLEMENTATION_COMPLETE.md | 文档 |
| IMPLEMENTATION_SUMMARY.md | 文档 |
| Makefile | 构建 |
| package.json | 依赖 |
| package-lock.json | 依赖 |
| QUICK_START.md | 文档 |
| README.md | 文档 |
| start.bat | 脚本 |
| USAGE_GUIDE.md | 文档 |
| deploy-to-lighthouse.sh | 部署 |
| lighthouse-deploy.sh | 部署 |

---

## backend/ 核心

| 路径 | 说明 |
|------|------|
| main.py | 应用入口 |
| requirements.txt | Python 依赖 |
| debug_routes.py | 调试路由 |
| alembic/ | 数据库迁移 |
| app/ | 应用代码 |
| config/ | 后端配置 |
| scripts/ | 后端脚本 |
| tests/ | 测试 |

### app/ 子结构

| 目录 | 说明 |
|------|------|
| app/agents/ | 智能体（NPC、Coach、RL） |
| app/api/ | API 端点、中间件、路由 |
| app/core/ | 配置、数据库、Prompt |
| app/data/ | 种子数据 |
| app/engine/ | 编排、意图、状态 |
| app/infra/ | 网关、缓存、LLM、搜索 |
| app/models/ | 数据模型 |
| app/observability/ | 监控、追踪 |
| app/schemas/ | 请求/响应 Schema |
| app/services/ | 业务服务 |

### app/api/endpoints/ 端点文件

| 文件 | 路由前缀 |
|------|----------|
| admin.py | /api/v1/admin |
| admin_modules/analytics.py | /api/v1/admin/analytics |
| admin_modules/courses.py | /api/v1/admin/courses |
| admin_modules/evaluation.py | /api/v1/admin/evaluation |
| admin_modules/knowledge.py | /api/v1/admin/knowledge |
| admin_modules/personas.py | /api/v1/admin/personas |
| admin_modules/scenarios.py | /api/v1/admin/scenarios |
| cockpit.py | /api/v1/cockpit |
| copilot.py | /api/v1/copilot |
| courses_simple.py | /api/v1/courses |
| customers_simple.py | /api/v1/customers |
| deals.py | /api/v1/deals |
| health.py | /health |
| monitoring.py | /metrics |
| tasks_simple.py | /api/v1/tasks |
| websocket.py | /ws |

---

## frontend/ 核心

| 路径 | 说明 |
|------|------|
| package.json | 依赖 |
| vite.config.ts | Vite 配置 |
| tailwind.config.js | Tailwind 配置 |
| tsconfig.json | TypeScript 配置 |
| src/App.tsx | 根组件 |
| src/index.css | 全局样式 |
| public/copilot.js | Copilot SDK |
| public/copilot-sdk.md | SDK 文档 |

### frontend/src/ 结构

| 目录 | 说明 |
|------|------|
| components/ | UI 组件 |
| config/ | 环境配置 |
| hooks/ | React Hooks |
| layouts/ | 布局 |
| lib/ | 工具库 |
| pages/ | 页面 |
| services/ | API 服务 |
| store/ | 状态 |
| utils/ | 工具函数 |

### pages/ 页面文件

| 路径 | 页面 |
|------|------|
| Admin/Analysis.tsx | 能力分析 |
| Admin/Cockpit.tsx | 总裁驾驶舱 |
| Admin/Courses.tsx | 课程管理 |
| Admin/Dashboard.tsx | Admin 仪表盘 |
| Admin/KnowledgeBase.tsx | 知识库 |
| Admin/Tasks.tsx | 任务管理 |
| Admin/Users.tsx | 用户管理 |
| auth/LoginPage.tsx | 登录 |
| settings/AdvancedSettings.tsx | 高级设置 |
| student/BattleCenter.tsx | 对战中心 |
| student/BattlePrep.tsx | 对战准备 |
| student/CourseList.tsx | 课程列表 |
| student/CustomerList.tsx | 客户预演 |
| student/Dashboard.tsx | 学员仪表盘 |
| student/Evaluation.tsx | 评估 |
| student/History.tsx | 历史 |
| student/LiveAssist.tsx | 实时协助 |
| student/Pipeline.tsx | 销售管道 |
| student/Review.tsx | 复盘 |
| student/Training.tsx | 训练 |

### services/ 服务文件

| 文件 | 说明 |
|------|------|
| api.ts | API 客户端 |
| analytics.service.ts | 分析 |
| course.service.ts | 课程 |
| customer.service.ts | 客户 |
| deal.service.ts | 商机 |
| knowledge.service.ts | 知识库 |
| task.service.ts | 任务 |
| session.service.ts | 会话 |
| scenario.service.ts | 场景 |
| adminMockData.ts | Mock（仅测试） |
| mockData.ts | Mock（仅测试） |

---

## deployment/

| 路径 | 说明 |
|------|------|
| docker/ | Docker 配置 |
| kubernetes/ | K8s 配置 |
| nginx/ | Nginx 配置 |
| monitoring/ | Prometheus/Grafana |
| scripts/ | 部署脚本 |
| cloud/ | 云平台配置 |

---

## docs/

| 路径 | 说明 |
|------|------|
| architecture/ | 架构文档 |
| crawlers/ | 爬虫说明 |
| deployment/ | 部署指南 |
| guides/ | 使用指南 |
| plans/ | 规划 |
| reports/ | 报告 |
| archive/ | 归档 |

---

## data/

| 路径 | 说明 |
|------|------|
| intent/ | 意图训练数据 |
| processed/ | 处理后数据 |
| raw/ | 原始数据 |
| seeds/ | 种子数据 |

---

## scripts/

| 路径 | 说明 |
|------|------|
| start.bat | 启动脚本 |
| dev.sh | 开发脚本 |
| setup.sh | 安装脚本 |
| deployment/ | 部署脚本 |
| ops/ | 运维脚本 |
