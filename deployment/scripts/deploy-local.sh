#!/bin/bash
# SalesBoost 部署脚本 - 北京服务器

set -e

echo "==================================="
echo "SalesBoost 部署开始"
echo "==================================="

# 停止并删除旧容器
echo "步骤 1: 清理旧容器..."
docker stop salesboost-backend salesboost-frontend salesboost-nginx salesboost-redis 2>/dev/null || true
docker rm salesboost-backend salesboost-frontend salesboost-nginx salesboost-redis 2>/dev/null || true

# 删除旧镜像
echo "步骤 2: 清理旧镜像..."
docker rmi salesboost-backend salesboost-frontend 2>/dev/null || true

# 创建数据目录
echo "步骤 3: 创建数据目录..."
mkdir -p /root/salesboost/logs
mkdir -p /root/salesboost/data
mkdir -p /root/salesboost/nginx

# 检查必要的文件
echo "步骤 4: 检查项目文件..."
if [ ! -f "/root/salesboost/docker-compose.yml" ]; then
    echo "错误: docker-compose.yml 不存在"
    exit 1
fi

if [ ! -f "/root/salesboost/Dockerfile.backend" ]; then
    echo "错误: Dockerfile.backend 不存在"
    exit 1
fi

if [ ! -f "/root/salesboost/Dockerfile.frontend" ]; then
    echo "错误: Dockerfile.frontend 不存在"
    exit 1
fi

# 检查 app 目录
if [ ! -d "/root/salesboost/app" ]; then
    echo "错误: app 目录不存在"
    exit 1
fi

# 检查 requirements.txt
if [ ! -f "/root/salesboost/requirements.txt" ]; then
    echo "错误: requirements.txt 不存在"
    exit 1
fi

# 构建后端镜像
echo "步骤 5: 构建后端镜像..."
cd /root/salesboost
docker build -f Dockerfile.backend -t salesboost-backend:latest .

# 构建前端镜像
echo "步骤 6: 构建前端镜像..."
docker build -f Dockerfile.frontend -t salesboost-frontend:latest ./frontend

# 启动服务
echo "步骤 7: 启动服务..."
docker-compose up -d

# 等待服务启动
echo "步骤 8: 等待服务启动..."
sleep 10

# 检查服务状态
echo "步骤 9: 检查服务状态..."
docker ps

echo "==================================="
echo "部署完成!"
echo "访问地址: http://101.43.199.144"
echo "后端 API: http://101.43.199.144/api"
echo "==================================="
