#!/bin/bash

# SalesBoost RAG 3.0 测试运行脚本

set -e

echo "🧪 SalesBoost RAG 3.0 测试套件"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest 未安装${NC}"
    echo "安装: pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

echo -e "${GREEN}✅ pytest 环境检查通过${NC}"
echo ""

# 运行单元测试
echo -e "${BLUE}📦 运行单元测试...${NC}"
pytest tests/unit/ -v --tb=short --cov=app --cov-report=term-missing

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 单元测试通过${NC}"
else
    echo -e "${RED}❌ 单元测试失败${NC}"
    exit 1
fi

echo ""

# 运行集成测试
echo -e "${BLUE}🔗 运行集成测试...${NC}"
pytest tests/integration/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 集成测试通过${NC}"
else
    echo -e "${YELLOW}⚠️  集成测试失败（可能需要配置 API keys）${NC}"
fi

echo ""

# 生成覆盖率报告
echo -e "${BLUE}📊 生成覆盖率报告...${NC}"
pytest tests/ --cov=app --cov-report=html --cov-report=term

echo ""
echo "================================"
echo -e "${GREEN}🎉 测试完成！${NC}"
echo "================================"
echo ""
echo "覆盖率报告: htmlcov/index.html"
echo ""
