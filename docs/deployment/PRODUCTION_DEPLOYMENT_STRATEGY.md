# SalesBoost 生产环境部署策略
## 完整的在线部署方案

**日期**: 2026-02-03
**状态**: ✅ 准备就绪
**GitHub**: https://github.com/Benjamindaoson/SalesBoost

---

## 📋 部署概览

### 推荐方案：前后端分离部署

**后端 (FastAPI + PostgreSQL + Redis)**:
- 平台: **Render.com** (推荐) 或 Railway.app
- 成本: $14-25/月
- 优势: 自动部署、SSL证书、数据库集成

**前端 (React + Vite)**:
- 平台: **Vercel** (推荐) 或 Netlify
- 成本: 免费
- 优势: 全球CDN、自动构建、零配置

---

## 🎯 部署架构

```
用户请求
    ↓
[Vercel CDN] - React前端 (全球加速)
    ↓
[Render.com] - FastAPI后端
    ├── PostgreSQL (数据库)
    ├── Redis (缓存)
    └── Qdrant (向量数据库 - 可选云服务)
```

---

## 📦 第一步：后端部署 (Render.com)

### 1.1 创建 Render 账号

1. 访问 https://render.com
2. 使用 GitHub 账号登录
3. 授权访问 SalesBoost 仓库

### 1.2 部署 PostgreSQL 数据库

1. 点击 "New +" → "PostgreSQL"
2. 配置:
   - **Name**: `salesboost-db`
   - **Database**: `salesboost`
   - **User**: `salesboost`
   - **Region**: Singapore (最近的亚洲节点)
   - **Plan**: Starter ($7/月) 或 Free (开发测试)
3. 点击 "Create Database"
4. **保存连接信息** (稍后需要):
   - Internal Database URL
   - External Database URL

### 1.3 部署 Redis

1. 点击 "New +" → "Redis"
2. 配置:
   - **Name**: `salesboost-redis`
   - **Region**: Singapore
   - **Plan**: Starter ($7/月) 或 Free
3. 点击 "Create Redis"
4. **保存连接 URL**

### 1.4 部署后端应用

1. 点击 "New +" → "Web Service"
2. 连接 GitHub 仓库: `Benjamindaoson/SalesBoost`
3. 配置:
   - **Name**: `salesboost-api`
   - **Region**: Singapore
   - **Branch**: `refactor/production-ready` (或 `main`)
   - **Root Directory**: 留空
   - **Runtime**: Docker
   - **Dockerfile Path**: `deployment/docker/Dockerfile.production`
   - **Plan**: Starter ($7/月) 或 Free

4. **环境变量配置** (点击 "Advanced" → "Add Environment Variable"):

```bash
# 核心配置
ENV_STATE=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库 (从 Render PostgreSQL 复制)
DATABASE_URL=<从 Render PostgreSQL 复制 Internal Database URL>

# Redis (从 Render Redis 复制)
REDIS_URL=<从 Render Redis 复制连接 URL>

# 安全密钥 (生成随机字符串)
SECRET_KEY=<使用以下命令生成: openssl rand -hex 32>

# LLM API Keys (必需)
SILICONFLOW_API_KEY=<你的 SiliconFlow API Key>
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 可选: 其他 LLM 提供商
OPENAI_API_KEY=<可选>
DASHSCOPE_API_KEY=<可选，用于 PDF OCR>

# CORS (前端域名，稍后更新)
CORS_ORIGINS=https://salesboost.vercel.app,http://localhost:5173
ALLOWED_HOSTS=salesboost-api.onrender.com

# 功能开关
COORDINATOR_ENGINE=langgraph
AGENTIC_V3_ENABLED=true
TOOL_CACHE_ENABLED=true
RAG_HYBRID_ENABLED=true

# 性能配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
WORKERS=2
```

5. **健康检查**:
   - Health Check Path: `/health/live`
   - 点击 "Create Web Service"

6. **等待部署** (约 5-10 分钟)
   - 查看日志确认启动成功
   - 记录后端 URL: `https://salesboost-api.onrender.com`

### 1.5 初始化数据库

部署完成后，运行数据库迁移:

1. 在 Render Dashboard 中，进入 `salesboost-api` 服务
2. 点击 "Shell" 标签
3. 运行以下命令:

```bash
# 运行数据库迁移
alembic upgrade head

# 验证连接
python -c "from app.core.database import engine; print('✅ Database connected')"
```

---

## 🌐 第二步：前端部署 (Vercel)

### 2.1 创建 Vercel 账号

1. 访问 https://vercel.com
2. 使用 GitHub 账号登录
3. 授权访问 SalesBoost 仓库

### 2.2 部署前端应用

1. 点击 "Add New..." → "Project"
2. 选择 `Benjamindaoson/SalesBoost` 仓库
3. 配置:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

4. **环境变量配置**:

```bash
# 后端 API 地址 (使用 Render 后端 URL)
VITE_API_URL=https://salesboost-api.onrender.com/api/v1

# Supabase (如果使用)
VITE_SUPABASE_URL=<你的 Supabase URL>
VITE_SUPABASE_ANON_KEY=<你的 Supabase Key>

# 功能开关
VITE_ENABLE_AI_FEATURES=true
VITE_ENABLE_ANALYTICS=false
```

5. 点击 "Deploy"
6. **等待部署** (约 2-3 分钟)
7. 记录前端 URL: `https://salesboost.vercel.app`

### 2.3 更新后端 CORS 配置

1. 返回 Render Dashboard
2. 进入 `salesboost-api` 服务
3. 更新环境变量:

```bash
CORS_ORIGINS=https://salesboost.vercel.app,http://localhost:5173
```

4. 保存并重新部署

---

## 🔧 第三步：配置向量数据库 (可选)

### 选项 A: 使用 Qdrant Cloud (推荐)

1. 访问 https://cloud.qdrant.io
2. 创建免费集群
3. 获取 API Key 和 URL
4. 在 Render 后端添加环境变量:

```bash
QDRANT_URL=<Qdrant Cloud URL>
QDRANT_API_KEY=<Qdrant API Key>
```

### 选项 B: 自托管 Qdrant (Docker)

如果使用 Render 的 Docker 部署，可以在 `docker-compose.production.yml` 中包含 Qdrant 服务。

---

## ✅ 第四步：验证部署

### 4.1 后端健康检查

```bash
# 健康检查
curl https://salesboost-api.onrender.com/health/live

# 预期响应
{"status": "healthy", "timestamp": "2026-02-03T..."}
```

### 4.2 前端访问测试

1. 访问 `https://salesboost.vercel.app`
2. 点击 "Demo Login" 或输入邮箱登录
3. 验证以下功能:
   - ✅ 仪表板加载
   - ✅ 任务列表显示
   - ✅ 导航菜单工作
   - ✅ API 调用成功

### 4.3 端到端测试

```bash
# 测试语义搜索
curl -X POST https://salesboost-api.onrender.com/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "如何处理价格异议", "top_k": 3}'

# 测试 Agent 对话
curl -X POST https://salesboost-api.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "我想练习处理客户异议", "session_id": "test-123"}'
```

---

## 📊 第五步：监控与优化

### 5.1 设置监控

**Render 内置监控**:
- CPU/内存使用率
- 请求延迟
- 错误率

**可选: 外部监控**:
1. **Sentry** (错误追踪):
   - 注册 https://sentry.io
   - 获取 DSN
   - 添加环境变量: `SENTRY_DSN=<your-dsn>`

2. **Prometheus + Grafana** (性能监控):
   - 后端已内置 `/api/monitoring/metrics` 端点
   - 可以连接到 Grafana Cloud

### 5.2 性能优化

**后端优化**:
```bash
# 启用缓存
TOOL_CACHE_ENABLED=true
SEMANTIC_CACHE_ENABLED=true

# 调整工作进程 (根据实例大小)
WORKERS=2  # 512MB RAM
WORKERS=4  # 1GB RAM
```

**前端优化**:
- Vercel 自动提供全球 CDN
- 自动代码分割和压缩
- 图片优化

---

## 💰 成本估算

### 免费方案 (开发/测试)
- **Render Free**: 后端 + PostgreSQL + Redis (有休眠限制)
- **Vercel Free**: 前端 (100GB 带宽/月)
- **Qdrant Cloud Free**: 1GB 向量存储
- **总计**: $0/月

### 生产方案 (推荐)
- **Render Starter**: $7/月 (后端)
- **Render PostgreSQL**: $7/月 (数据库)
- **Render Redis**: $7/月 (缓存)
- **Vercel Pro**: $20/月 (可选，更高带宽)
- **Qdrant Cloud**: $25/月 (可选，更大存储)
- **总计**: $21-66/月

### 高流量方案
- **Render Standard**: $25/月 (后端)
- **Render PostgreSQL**: $20/月 (数据库)
- **Render Redis**: $10/月 (缓存)
- **Vercel Pro**: $20/月 (前端)
- **Qdrant Cloud**: $95/月 (生产级)
- **Sentry**: $26/月 (错误追踪)
- **总计**: $196/月

---

## 🔒 安全检查清单

- [ ] 所有 API Keys 存储在环境变量中
- [ ] 数据库使用 SSL 连接
- [ ] CORS 正确配置 (仅允许前端域名)
- [ ] HTTPS 强制启用
- [ ] 速率限制已启用
- [ ] 敏感日志已过滤
- [ ] 定期备份数据库
- [ ] 密钥定期轮换

---

## 🚀 部署时间线

### 第一天 (2-3 小时)
- [x] 创建 Render 账号
- [ ] 部署 PostgreSQL (15 分钟)
- [ ] 部署 Redis (10 分钟)
- [ ] 部署后端应用 (30 分钟)
- [ ] 初始化数据库 (10 分钟)
- [ ] 创建 Vercel 账号
- [ ] 部署前端应用 (20 分钟)
- [ ] 配置 CORS (5 分钟)
- [ ] 端到端测试 (30 分钟)

### 第二天 (1-2 小时)
- [ ] 配置向量数据库 (30 分钟)
- [ ] 设置监控 (30 分钟)
- [ ] 性能优化 (30 分钟)
- [ ] 文档更新 (30 分钟)

### 第三天 (持续)
- [ ] 用户验收测试
- [ ] 监控生产指标
- [ ] 根据反馈优化

---

## 🆘 常见问题

### Q1: 后端启动失败
**原因**: 环境变量配置错误
**解决**: 检查 `DATABASE_URL` 和 `REDIS_URL` 是否正确

### Q2: 前端无法连接后端
**原因**: CORS 配置问题
**解决**: 确保后端 `CORS_ORIGINS` 包含前端域名

### Q3: 数据库连接超时
**原因**: 使用了 External URL 而非 Internal URL
**解决**: 在 Render 内部服务间使用 Internal Database URL

### Q4: 向量搜索失败
**原因**: Qdrant 未配置或数据未导入
**解决**: 配置 Qdrant 并运行数据导入脚本

### Q5: 部署后性能慢
**原因**: 免费实例休眠或资源不足
**解决**: 升级到 Starter 计划 ($7/月)

---

## 📞 支持与维护

### 日常任务
- 检查健康端点
- 查看错误日志
- 监控响应时间

### 每周任务
- 审查性能指标
- 检查数据库大小
- 更新依赖 (如需要)

### 每月任务
- 备份知识库
- 审查和优化查询
- 更新文档

---

## 🎯 成功指标

### 技术指标
- **正常运行时间**: >99.5%
- **响应时间**: <100ms (p95)
- **错误率**: <1%
- **内存使用**: <80% 容量

### 业务指标
- 每日用户查询数
- 查询成功率
- 用户满意度评分
- 知识库覆盖率

---

## 📚 相关文档

- [GitHub 仓库](https://github.com/Benjamindaoson/SalesBoost)
- [云部署指南](./CLOUD_DEPLOYMENT_GUIDE.md)
- [前端部署文档](../../frontend/DEPLOYMENT.md)
- [操作手册](../OPERATIONS_MANUAL.md)
- [快速参考](../QUICK_REFERENCE.md)

---

## 🎉 下一步

1. **立即开始**: 按照上述步骤部署到 Render + Vercel
2. **配置域名**: 绑定自定义域名 (可选)
3. **启用监控**: 设置 Sentry 和性能监控
4. **用户测试**: 邀请用户测试并收集反馈
5. **持续优化**: 根据生产数据优化性能

---

**部署状态**: ✅ 准备就绪
**预计部署时间**: 2-3 小时
**推荐平台**: Render.com (后端) + Vercel (前端)
**月度成本**: $21-66 (生产环境)

---

**最后更新**: 2026-02-03
**版本**: 1.0.0
**状态**: 生产就绪
