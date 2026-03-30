#!/bin/bash
# SalesBoost 一键部署脚本 - 阿里云
# 使用方法: ./deploy_aliyun.sh

set -e

echo "🚀 SalesBoost 阿里云部署开始..."

# 配置信息（请修改）
SERVER_IP="你的服务器IP"
SERVER_USER="root"
DOMAIN="你的域名.com"

echo "📋 部署配置:"
echo "  服务器: $SERVER_IP"
echo "  域名: $DOMAIN"
echo ""
read -p "确认配置正确？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# 1. 上传代码到服务器
echo "📤 上传代码..."
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
    ./ $SERVER_USER@$SERVER_IP:/opt/salesboost/

# 2. SSH 到服务器执行部署
echo "🔧 在服务器上执行部署..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
cd /opt/salesboost

# 安装 Docker
if ! command -v docker &> /dev/null; then
    echo "📦 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
fi

# 安装 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 创建 .env.production 文件
echo "⚙️ 配置环境变量..."
cat > .env.production << 'EOF'
ENV_STATE=production
DEBUG=false
LOG_LEVEL=INFO

# 数据库（Docker 内部）
DATABASE_URL=postgresql+asyncpg://salesboost:changeme@postgres:5432/salesboost
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333

# 请手动填写以下 API Keys
SILICONFLOW_API_KEY=
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_JWT_SECRET=

# CORS
CORS_ORIGINS=https://你的域名.com,http://localhost:3000
ALLOWED_HOSTS=你的域名.com,localhost

# 功能开关
AGENTIC_V3_ENABLED=true
COORDINATOR_ENGINE=langgraph
ENABLE_ML_INTENT=true
EOF

echo "⚠️ 请编辑 .env.production 填写 API Keys"
echo "vim .env.production"
read -p "填写完成后按回车继续..."

# 构建前端
echo "🏗️ 构建前端..."
cd frontend
npm install
npm run build
cd ..

# 启动服务
echo "🚀 启动服务..."
docker-compose -f docker-compose.production.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查健康状态
echo "🏥 检查服务健康..."
curl -f http://localhost:8000/health || echo "⚠️ 后端服务未就绪"

echo "✅ 服务启动完成！"
docker-compose -f docker-compose.production.yml ps

ENDSSH

# 3. 配置 Nginx 和 SSL
echo "🔒 配置 Nginx 和 SSL..."
ssh $SERVER_USER@$SERVER_IP << ENDSSH2
# 安装 Nginx
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

# 配置 Nginx
cat > /etc/nginx/sites-available/salesboost << 'EOF'
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/salesboost /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 申请 SSL 证书
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

echo "✅ SSL 证书配置完成！"
ENDSSH2

echo ""
echo "🎉 部署完成！"
echo "🌐 访问地址: https://$DOMAIN"
echo "📊 健康检查: https://$DOMAIN/health"
echo "📈 Grafana: https://$DOMAIN:3000 (admin/admin)"
echo ""
echo "📝 后续步骤:"
echo "1. 修改 Grafana 密码"
echo "2. 配置域名 DNS 解析到 $SERVER_IP"
echo "3. 在 .env.production 中填写所有 API Keys"
