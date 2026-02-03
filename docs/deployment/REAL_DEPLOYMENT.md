# SalesBoost 真正的部署指南

## 🎯 三种部署方式（都是真部署，用户可以访问）

### 方式1：Railway（最简单，5分钟）

**优点**: 一键部署，自动配置域名和SSL，免费额度够用
**缺点**: 国外服务器，国内访问可能慢

```bash
# 1. 安装 Railway CLI
npm install -g @railway/cli

# 2. 运行部署脚本
chmod +x deploy_railway.sh
./deploy_railway.sh

# 3. 设置 API Keys（在 Railway 网页控制台）
# 访问 railway.app，在 Variables 中设置：
# - SILICONFLOW_API_KEY
# - OPENAI_API_KEY
# - SUPABASE_URL
# - SUPABASE_KEY

# 4. 获取访问地址
railway domain
# 会得到类似: https://salesboost-production.up.railway.app
```

### 方式2：阿里云（国内访问快）

**优点**: 国内访问快，稳定
**缺点**: 需要购买服务器（最低配置约60元/月）

```bash
# 1. 购买阿里云 ECS（1核2G即可）
# 访问: https://ecs.console.aliyun.com

# 2. 购买域名（可选，也可以用IP访问）
# 访问: https://dc.console.aliyun.com

# 3. 修改部署脚本中的配置
vim deploy_aliyun.sh
# 修改: SERVER_IP 和 DOMAIN

# 4. 运行部署
chmod +x deploy_aliyun.sh
./deploy_aliyun.sh

# 5. 访问你的域名
# https://你的域名.com
```

### 方式3：Docker Compose（本地或任何服务器）

**优点**: 完全控制，可以部署到任何有Docker的服务器
**缺点**: 需要手动配置域名和SSL

```bash
# 1. 创建 .env.production 文件
cp .env.example .env.production
vim .env.production
# 填写所有必需的 API Keys

# 2. 构建前端
cd frontend
npm install
npm run build
cd ..

# 3. 启动所有服务
docker-compose -f docker-compose.production.yml up -d

# 4. 检查服务状态
docker-compose -f docker-compose.production.yml ps
curl http://localhost:8000/health

# 5. 访问应用
# 前端: http://localhost:80
# 后端: http://localhost:8000
# Grafana: http://localhost:3000
```

## 🔑 必需的环境变量

无论哪种部署方式，都需要设置这些：

```bash
# LLM API Keys（至少一个）
SILICONFLOW_API_KEY=sk-xxx  # 用于 DeepSeek
OPENAI_API_KEY=sk-xxx        # 用于 GPT

# 认证（如果使用 Supabase）
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx
SUPABASE_JWT_SECRET=xxx

# 数据库（Railway/Render 会自动配置）
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

## 📊 部署后检查

```bash
# 1. 健康检查
curl https://你的域名/health

# 2. 查看日志
docker-compose -f docker-compose.production.yml logs -f

# 3. 监控
# 访问 Grafana: https://你的域名:3000
```

## 🆘 常见问题

### Q: 部署后无法访问？
A: 检查防火墙是否开放端口 80, 443, 8000

### Q: API 调用失败？
A: 检查 .env.production 中的 API Keys 是否正确

### Q: 前端无法连接后端？
A: 检查 VITE_API_URL 是否指向正确的后端地址

## 🎉 部署成功后

你会得到一个公网可访问的地址，例如：
- Railway: `https://salesboost-production.up.railway.app`
- 阿里云: `https://你的域名.com`
- 本地: `http://你的服务器IP`

所有用户都可以通过这个统一的网址访问使用！
