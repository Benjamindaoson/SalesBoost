#!/bin/bash

# SalesBoost Lighthouse 部署脚本

echo "=== SalesBoost Lighthouse 部署开始 ==="

# 1. 构建前端
echo "步骤 1: 构建前端..."
cd frontend
npm install
npm run build
cd ..

# 检查构建是否成功
if [ ! -d "frontend/dist" ]; then
    echo "错误: 前端构建失败"
    exit 1
fi

echo "=== 准备部署文件 ==="
echo "后端: backend/"
echo "前端构建: frontend/dist/"
echo "配置: deployment/docker/"

echo "=== 准备完成,等待上传到服务器 ==="
