#!/bin/bash
# SalesBoost 一键部署脚本 - Railway
# 使用方法: ./deploy_railway.sh

set -e

echo "🚀 SalesBoost Railway 部署开始..."

# 1. 检查 Railway CLI
if ! command -v railway &> /dev/null; then
    echo "📦 安装 Railway CLI..."
    npm install -g @railway/cli
fi

# 2. 登录 Railway
echo "🔐 登录 Railway..."
railway login

# 3. 创建新项目
echo "📁 创建项目..."
railway init

# 4. 添加 PostgreSQL
echo "🗄️ 添加 PostgreSQL..."
railway add --database postgres

# 5. 添加 Redis
echo "💾 添加 Redis..."
railway add --database redis

# 6. 设置环境变量
echo "⚙️ 配置环境变量..."
railway variables set ENV_STATE=production
railway variables set DEBUG=false
railway variables set LOG_LEVEL=INFO

# 需要你手动设置的 API Keys
echo ""
echo "⚠️ 请手动设置以下环境变量:"
echo "railway variables set SILICONFLOW_API_KEY=你的key"
echo "railway variables set OPENAI_API_KEY=你的key"
echo "railway variables set SUPABASE_URL=你的url"
echo "railway variables set SUPABASE_KEY=你的key"
echo ""
read -p "已设置完成？按回车继续..."

# 7. 部署
echo "🚀 开始部署..."
railway up

# 8. 获取域名
echo "🌐 获取访问地址..."
DOMAIN=$(railway domain)

echo ""
echo "✅ 部署完成！"
echo "🌐 访问地址: https://$DOMAIN"
echo "📊 健康检查: https://$DOMAIN/health"
echo "📈 监控面板: railway open"
