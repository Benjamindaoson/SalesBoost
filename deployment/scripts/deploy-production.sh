#!/bin/bash

# SalesBoost Gold Master Production Deployment Script
# Orchestrates full stack deployment with Docker, Nginx, SSL, and DB migrations.

set -e

echo "🚀 Starting SalesBoost Production Deployment..."

# 1. Environment Sanity Check
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production not found. Create it from .env.production.example"
    exit 1
fi

source .env.production

echo "✅ Environment check passed."

# 2. Pre-flight Checks (Lint & Sanity)
echo "🔍 Running pre-flight checks..."
python scripts/ops/preflight_check.py

# 3. Build & Package
echo "🔨 Building Docker images (Frontend + Backend + Gateway)..."
docker-compose -f deployment/docker/docker-compose.production.yml build

# 4. Infrastructure Startup (Databases)
echo "🗄️  Starting database services (Postgres, Redis, Qdrant)..."
docker-compose -f deployment/docker/docker-compose.production.yml up -d postgres redis qdrant

echo "⏳ Waiting for databases to initialize..."
sleep 10

# 5. Database Migrations & Seeding
echo "🔄 Running database migrations..."
docker-compose -f deployment/docker/docker-compose.production.yml run --rm salesboost alembic upgrade head

echo "🌱 Seeding initial data..."
docker-compose -f deployment/docker/docker-compose.production.yml run --rm salesboost python scripts/deployment/init_database.py

# 6. Start Application Services
echo "🚀 Starting backend and worker services..."
docker-compose -f deployment/docker/docker-compose.production.yml up -d salesboost worker

# 7. Start Nginx Gateway
echo "🌐 Starting Nginx Gateway..."
docker-compose -f deployment/docker/docker-compose.production.yml up -d gateway

# 8. SSL Initialization (Optional/If configured)
if [ "$ENABLE_SSL" = "true" ]; then
    echo "🔒 Initializing SSL with Certbot..."
    # Placeholder for certbot initialization command
    # docker-compose -f deployment/docker/docker-compose.production.yml run --rm certbot certonly --webroot ...
fi

# 9. Verification
echo "🏥 Performing health checks..."
MAX_RETRIES=30
RETRY_COUNT=0
HEALTH_URL="http://localhost:8000/health/live"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f "$HEALTH_URL" &> /dev/null; then
        echo "✅ Backend service is HEALTHY."
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for service... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Error: Service failed to reach healthy state."
    docker-compose -f deployment/docker/docker-compose.production.yml logs salesboost
    exit 1
fi

echo "===================================================="
echo "🎉 SalesBoost Deployment COMPLETED successfully!"
echo "===================================================="
echo "Main Application: http://localhost (or configured domain)"
echo "API Docs: http://localhost/docs"
echo "Monitoring (Grafana): http://localhost:3000"
echo "Metrics (Prometheus): http://localhost:9090"
echo "===================================================="
