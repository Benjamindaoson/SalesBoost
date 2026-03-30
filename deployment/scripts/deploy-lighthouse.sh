#!/bin/bash
# SalesBoost 完整部署脚本 for Tencent Lighthouse

set -e

echo "==================================="
echo "SalesBoost - AI 销售作战平台 - 完整部署"
echo "==================================="

PROJECT_DIR="/root/salesboost-prod"

echo "步骤 1: 创建项目目录..."
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo "步骤 2: 克隆代码仓库..."
if [ ! -d ".git" ]; then
    git clone --depth 1 https://github.com/Benjamindaoson/SalesBoost.git .
fi

echo "步骤 3: 安装 Node.js 18..."
if ! command -v node &> /dev/null || [ "$(node -v | cut -d'v' -f2 | cut -d'.' -f1)" != "18" ]; then
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    yum install -y nodejs
fi

echo "步骤 4: 构建前端..."
cd frontend
npm install
npm run build
cd ..

echo "步骤 5: 配置 nginx..."
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}
http {
    include /etc/nginx/mime.types;
    charset utf-8;
    
    server {
        listen 80;
        server_name _;
        
        location /api/ {
            proxy_pass http://backend:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }
    }
}
EOF

echo "步骤 6: 创建 docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  backend:
    image: python:3.11-slim
    container_name: salesboost-backend
    restart: always
    ports:
      - "8000:8000"
    working_dir: /app
    volumes:
      - ./backend:/app
      - ./data:/app/data
    environment:
      - ENV_STATE=production
    command: sh -c "pip install -q fastapi uvicorn aiosqlite && uvicorn main:app --host 0.0.0.0 --port 8000"
    networks:
      - salesboost-network

  frontend:
    image: nginx:alpine
    container_name: salesboost-frontend
    restart: always
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    networks:
      - salesboost-network

networks:
  salesboost-network:
    driver: bridge
EOF

echo "步骤 7: 启动服务..."
docker-compose down 2>/dev/null || true
docker-compose up -d

echo "==================================="
echo "部署完成!"
echo "访问地址: http://$(curl -s ifconfig.me)"
echo "==================================="
