#!/bin/bash
# 在服务器上创建 SalesBoost 项目结构

set -e

echo "==================================="
echo "初始化 SalesBoost 项目结构"
echo "==================================="

# 创建主目录
mkdir -p /root/salesboost
cd /root/salesboost

# 创建必要的子目录
mkdir -p logs/nginx
mkdir -p data
mkdir -p nginx/ssl

echo "目录结构创建完成"
ls -la /root/salesboost
