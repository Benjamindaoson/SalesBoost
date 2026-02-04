# SalesBoost Render 后端部署完整指南
## 手动部署步骤（已验证可行）

**日期**: 2026-02-03
**状态**: ✅ 配置已就绪
**预计时间**: 30-40 分钟

---

## 🎯 部署概览

你将创建：
1. **PostgreSQL 数据库** - 存储应用数据
2. **Redis 实例** - 缓存和会话管理
3. **Web Service** - FastAPI 后端应用

**总成本**: $21/月 (Starter 计划)

---

## 📋 准备工作

### 已准备好的内容
- ✅ GitHub 仓库: https://github.com/Benjamindaoson/SalesBoost
- ✅ Dockerfile: `deployment/docker/Dockerfile.production`
- ✅ 环境变量配置: 已在下方列出
- ✅ SiliconFlow API Key: `sk-snmxtfurdqafrgyeppwefsihzwsqolsashzhhtvwhlkxvjib`

---

## 🚀 步骤 1: 创建 PostgreSQL 数据库

1. **登录 Render**
   - 访问: https://dashboard.render.com
   - 使用你的账号登录

2. **创建新数据库**
   - 点击右上角 **"New +"**
   - 选择 **"PostgreSQL"**

3. **配置数据库**
   ```
   Name: salesboost-db
   Database: salesboost
   User: salesboost
   Region: Singapore (或最近的亚洲节点)
   PostgreSQL Version: 16 (默认)
   Plan: Starter ($7/月)
   ```

4. **创建并等待**
   - 点击 **"Create Database"**
   - 等待 2-3 分钟直到状态变为 "Available"

5. **保存连接信息** ⚠️ 重要！
   - 在数据库页面，找到 **"Connections"** 部分
   - 复制 **"Internal Database URL"** (格式: `postgresql://...`)
   - 保存到记事本，稍后需要

   示例格式:
   ```
   postgresql://salesboost:xxxxx@dpg-xxxxx-a.singapore-postgres.render.com/salesboost
   ```

---

## 🔴 步骤 2: 创建 Redis 实例

1. **创建新 Redis**
   - 点击 **"New +"**
   - 选择 **"Redis"**

2. **配置 Redis**
   ```
   Name: salesboost-redis
   Region: Singapore (与数据库相同)
   Plan: Starter ($7/月)
   Maxmemory Policy: allkeys-lru (默认)
   ```

3. **创建并等待**
   - 点击 **"Create Redis"**
   - 等待 1-2 分钟

4. **保存连接信息** ⚠️ 重要！
   - 在 Redis 页面，找到 **"Connections"** 部分
   - 复制 **"Internal Redis URL"** (格式: `redis://...`)
   - 保存到记事本

   示例格式:
   ```
   redis://red-xxxxx:6379
   ```

---

## 🌐 步骤 3: 部署后端应用

1. **创建 Web Service**
   - 点击 **"New +"**
   - 选择 **"Web Service"**

2. **连接 GitHub**
   - 选择 **"Build and deploy from a Git repository"**
   - 点击 **"Connect GitHub"** (如果还没连接)
   - 找到并选择 **"Benjamindaoson/SalesBoost"** 仓库
   - 点击 **"Connect"**

3. **基本配置**
   ```
   Name: salesboost-api
   Region: Singapore
   Branch: main
   Root Directory: (留空)
   Runtime: Docker
   ```

4. **Docker 配置**
   ```
   Dockerfile Path: deployment/docker/Dockerfile.production
   Docker Context: . (默认)
   Docker Build Args: (留空)
   ```

5. **实例配置**
   ```
   Instance Type: Web Service
   Plan: Starter ($7/月)
   ```

---

## ⚙️ 步骤 4: 配置环境变量

在 **"Environment"** 部分，点击 **"Add Environment Variable"**，逐个添加以下变量：

### 核心配置
```bash
ENV_STATE=production
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
```

### 数据库配置 ⚠️ 使用步骤1保存的 URL
```bash
DATABASE_URL=<粘贴步骤1保存的 Internal Database URL>
```

### Redis 配置 ⚠️ 使用步骤2保存的 URL
```bash
REDIS_URL=<粘贴步骤2保存的 Internal Redis URL>
```

### 安全配置
```bash
SECRET_KEY=<生成一个随机密钥，见下方说明>
```

**生成 SECRET_KEY**:
- Windows PowerShell:
  ```powershell
  -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
  ```
- 或使用在线工具: https://randomkeygen.com/ (选择 256-bit WPA Key)

### LLM API 配置
```bash
SILICONFLOW_API_KEY=sk-snmxtfurdqafrgyeppwefsihzwsqolsashzhhtvwhlkxvjib
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

### CORS 配置
```bash
CORS_ORIGINS=https://salesboost-benjamindaosons-projects.vercel.app,http://localhost:5173
ALLOWED_HOSTS=salesboost-api.onrender.com
```

### 功能开关
```bash
COORDINATOR_ENGINE=langgraph
AGENTIC_V3_ENABLED=true
TOOL_CACHE_ENABLED=true
RAG_HYBRID_ENABLED=true
ENABLE_ML_INTENT=true
ENABLE_CONTEXT_AWARE=true
```

### 性能配置
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
WORKERS=2
```

### 工具配置
```bash
TOOL_RETRY_ENABLED=true
TOOL_RETRY_MAX_ATTEMPTS=3
TOOL_PARALLEL_ENABLED=true
TOOL_PARALLEL_MAX_CONCURRENT=5
```

### RAG 配置
```bash
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.75
BGE_RERANKER_ENABLED=false
```

### 缓存配置
```bash
SEMANTIC_CACHE_ENABLED=true
SEMANTIC_CACHE_TTL_SECONDS=3600
TOOL_CACHE_LRU_ENABLED=true
```

### 监控配置
```bash
PROMETHEUS_ENABLED=true
TRACING_ENABLED=false
```

---

## 🏥 步骤 5: 配置健康检查

在 **"Health Check"** 部分:
```
Health Check Path: /health/live
```

---

## 🚀 步骤 6: 部署

1. **检查配置**
   - 确认所有环境变量已添加
   - 确认 Dockerfile 路径正确
   - 确认健康检查路径正确

2. **开始部署**
   - 点击页面底部的 **"Create Web Service"**
   - Render 将开始构建和部署

3. **监控部署**
   - 查看 **"Logs"** 标签实时查看部署日志
   - 预计需要 10-15 分钟

4. **等待成功**
   - 当看到 "Your service is live 🎉" 表示部署成功
   - 状态变为绿色 "Live"

---

## ✅ 步骤 7: 初始化数据库

部署成功后，需要运行数据库迁移：

1. **打开 Shell**
   - 在 `salesboost-api` 服务页面
   - 点击右上角的 **"Shell"** 标签

2. **运行迁移**
   ```bash
   # 运行数据库迁移
   alembic upgrade head
   ```

3. **验证连接**
   ```bash
   # 测试数据库连接
   python -c "from app.core.database import engine; print('✅ Database connected')"
   ```

4. **检查健康**
   ```bash
   # 测试应用健康
   curl http://localhost:8000/health/live
   ```

---

## 🔍 步骤 8: 验证部署

### 8.1 获取后端 URL

在服务页面顶部，你会看到类似这样的 URL:
```
https://salesboost-api.onrender.com
```

### 8.2 测试健康端点

在浏览器或命令行中访问:
```bash
curl https://salesboost-api.onrender.com/health/live
```

预期响应:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-03T...",
  "version": "1.0.0"
}
```

### 8.3 测试 API 文档

访问:
```
https://salesboost-api.onrender.com/docs
```

应该看到 FastAPI 自动生成的 API 文档。

---

## 🎯 步骤 9: 更新前端配置

部署成功后，需要更新前端的 API URL：

1. **登录 Vercel Dashboard**
   - 访问: https://vercel.com/dashboard

2. **进入项目**
   - 找到 `salesboost` 项目
   - 点击进入

3. **更新环境变量**
   - 点击 **"Settings"** 标签
   - 点击 **"Environment Variables"**
   - 找到 `VITE_API_URL`
   - 更新为: `https://salesboost-api.onrender.com/api/v1`
   - 点击 **"Save"**

4. **重新部署前端**
   - 点击 **"Deployments"** 标签
   - 点击最新部署右侧的 **"..."**
   - 选择 **"Redeploy"**

---

## 🆘 常见问题排查

### 问题 1: 部署失败 - "Failed to build"

**可能原因**: Docker 构建错误

**解决方法**:
1. 检查 Logs 标签查看具体错误
2. 确认 Dockerfile 路径: `deployment/docker/Dockerfile.production`
3. 确认 Branch 是 `main`

### 问题 2: 应用启动失败 - "Application failed to respond"

**可能原因**: 环境变量配置错误

**解决方法**:
1. 检查 `DATABASE_URL` 是否使用 Internal URL
2. 检查 `REDIS_URL` 是否正确
3. 检查 `SILICONFLOW_API_KEY` 是否有效
4. 在 Shell 中运行: `env | grep DATABASE_URL` 验证

### 问题 3: 数据库连接失败

**可能原因**: 使用了 External URL 而非 Internal URL

**解决方法**:
1. 返回 PostgreSQL 页面
2. 确认使用的是 **Internal Database URL**
3. Internal URL 格式: `postgresql://...@dpg-xxxxx-a.singapore-postgres.render.com/...`
4. External URL 格式: `postgresql://...@dpg-xxxxx-a.singapore-postgres.render.com:5432/...` (有端口号)

### 问题 4: 健康检查失败

**可能原因**: 健康检查路径错误

**解决方法**:
1. 确认健康检查路径是 `/health/live` (不是 `/health`)
2. 在 Shell 中测试: `curl http://localhost:8000/health/live`

### 问题 5: CORS 错误

**可能原因**: CORS_ORIGINS 配置不正确

**解决方法**:
1. 确认 `CORS_ORIGINS` 包含前端域名
2. 格式: `https://salesboost-benjamindaosons-projects.vercel.app,http://localhost:5173`
3. 注意逗号分隔，没有空格

---

## 📊 部署后检查清单

- [ ] PostgreSQL 数据库状态为 "Available"
- [ ] Redis 实例状态为 "Available"
- [ ] Web Service 状态为 "Live" (绿色)
- [ ] 健康检查通过: `/health/live` 返回 200
- [ ] API 文档可访问: `/docs`
- [ ] 数据库迁移已运行: `alembic upgrade head`
- [ ] 环境变量全部配置正确
- [ ] 前端 API URL 已更新
- [ ] CORS 配置正确

---

## 💰 成本明细

| 服务 | 计划 | 月度成本 |
|------|------|----------|
| PostgreSQL | Starter | $7 |
| Redis | Starter | $7 |
| Web Service | Starter | $7 |
| **总计** | | **$21** |

**免费试用**:
- Render 提供 $5 免费额度
- 可以先使用 Free 计划测试（有休眠限制）

---

## 📞 获取帮助

如果遇到问题：

1. **查看日志**
   - 在服务页面点击 "Logs" 标签
   - 查找错误信息

2. **使用 Shell**
   - 点击 "Shell" 标签
   - 运行诊断命令

3. **检查状态**
   - 确认所有服务都是 "Live" 或 "Available"
   - 检查健康检查是否通过

4. **参考文档**
   - Render 文档: https://render.com/docs
   - 项目文档: `docs/deployment/`

---

## 🎉 部署成功！

完成所有步骤后，你的后端将在以下地址运行：

**后端 API**: `https://salesboost-api.onrender.com`
**API 文档**: `https://salesboost-api.onrender.com/docs`
**健康检查**: `https://salesboost-api.onrender.com/health/live`

---

**创建日期**: 2026-02-03
**最后更新**: 2026-02-03
**状态**: ✅ 已验证可行
