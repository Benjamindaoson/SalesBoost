#!/bin/bash
# SalesBoost Production Deployment Script
# 100% Automated Go-Live

set -e

echo "🚀 Starting SalesBoost Production Deployment..."

# 1. Environment Check
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# 2. Docker Check
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    exit 1
fi

# 3. Build and Launch
echo "🏗️  Building and launching containers..."
docker-compose up -d --build

# 4. Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 20

# 5. Health Check
echo "🔍 Performing health check..."
if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo -e "\n✨ SalesBoost is now LIVE and 100% Operational!"
    echo "------------------------------------------------"
    echo "🌍 Frontend: http://localhost"
    echo "⚙️  Backend API: http://localhost:8000"
    echo "📊 Monitoring (Grafana): http://localhost:3001"
    echo "------------------------------------------------"
else
    echo "❌ Health check failed. Check logs with 'docker-compose logs api'"
fi
