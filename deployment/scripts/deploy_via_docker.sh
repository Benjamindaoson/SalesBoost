#!/bin/bash

# SalesBoost 部署脚本
# 用于在 Lighthouse 服务器上直接部署

set -e

echo "=========================================="
echo "SalesBoost 部署到 Lighthouse"
echo "=========================================="

# 更新系统
echo "1. 更新系统..."
sudo apt-get update && sudo apt-get upgrade -y

# 安装必要工具
echo "2. 安装必要工具..."
sudo apt-get install -y git curl wget docker.io docker-compose

# 启动 Docker
echo "3. 启动 Docker..."
sudo systemctl start docker
sudo systemctl enable docker

# 创建项目目录
echo "4. 创建项目目录..."
mkdir -p ~/salesboost
cd ~/salesboost

# 克隆项目（或者从其他方式获取）
echo "5. 获取项目文件..."
# 方式1: 从 Git 克隆
# git clone <your-repo-url> .

# 方式2: 从本地文件传输
# 请使用 scp 或其他方式传输文件

# 创建必要的目录
mkdir -p logs data nginx

# 创建环境变量文件
echo "6. 创建环境变量文件..."
cat > .env <<EOF
ENV_STATE=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite+aiosqlite:///./data/salesboost.db
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=$(openssl rand -hex 16)
CORS_ORIGINS=*
ALLOWED_HOSTS=*
EOF

# 启动服务
echo "7. 启动服务..."
sudo docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "8. 等待服务启动..."
sleep 30

# 检查服务状态
echo "9. 检查服务状态..."
sudo docker-compose ps

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo "后端 API: http://101.43.199.144:8000"
echo "前端界面: http://101.43.199.144"
echo ""
echo "查看日志:"
echo "  sudo docker-compose logs -f backend"
echo "  sudo docker-compose logs -f frontend"
echo ""
echo "停止服务:"
echo "  sudo docker-compose down"
echo ""
