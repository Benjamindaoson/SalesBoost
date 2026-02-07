#!/bin/bash

# SalesBoost RAG 3.0 生产部署脚本

set -e

echo "🚀 SalesBoost RAG 3.0 生产部署"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 环境检查通过${NC}"

# 检查环境变量文件
if [ ! -f .env.production ]; then
    echo -e "${YELLOW}⚠️  .env.production 不存在，从模板创建...${NC}"
    cp .env.production.example .env.production
    echo -e "${YELLOW}⚠️  请编辑 .env.production 配置生产环境变量${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 环境变量文件检查通过${NC}"

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p storage logs monitoring config/prometheus config/grafana config/nginx

# 构建 Docker 镜像
echo "🔨 构建 Docker 镜像..."
docker-compose -f docker-compose.production.yml build

# 启动数据库服务
echo "🗄️  启动数据库服务..."
docker-compose -f docker-compose.production.yml up -d postgres redis qdrant

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
sleep 10

# 运行数据库迁移
echo "🔄 运行数据库迁移..."
docker-compose -f docker-compose.production.yml run --rm salesboost alembic upgrade head

# 启动所有服务
echo "🚀 启动所有服务..."
docker-compose -f docker-compose.production.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 健康检查
echo "🏥 健康检查..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/api/health &> /dev/null; then
        echo -e "${GREEN}✅ 服务健康检查通过${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "等待服务启动... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ 服务启动失败${NC}"
    docker-compose -f docker-compose.production.yml logs salesboost
    exit 1
fi

# 显示服务状态
echo ""
echo "================================"
echo -e "${GREEN}🎉 部署成功！${NC}"
echo "================================"
echo ""
echo "服务地址："
echo "  - 主应用: http://localhost:8000"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo ""
echo "查看日志："
echo "  docker-compose -f docker-compose.production.yml logs -f salesboost"
echo ""
echo "停止服务："
echo "  docker-compose -f docker-compose.production.yml down"
echo ""
