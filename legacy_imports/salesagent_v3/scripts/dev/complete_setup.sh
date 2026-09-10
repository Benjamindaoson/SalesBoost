#!/bin/bash
# Complete Phase 1 Setup Script - Run this to set up everything

set -e

echo "馃殌 SalesAgent V3 - Phase 1 Complete Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "鉁?Python $python_version"

# Check Docker
echo ""
echo "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "鉂?Docker is not running. Please start Docker Desktop first."
    exit 1
fi
echo "鉁?Docker is running"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q -r requirements.txt
pip install -q itchat pycryptodome alembic
echo "鉁?Dependencies installed"

# Start infrastructure
echo ""
echo "Starting infrastructure (PostgreSQL, Redis, MinIO)..."
docker-compose -f docker-compose.dev.yml up -d postgres redis minio

# Wait for PostgreSQL
echo ""
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec salesagent-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "鉁?PostgreSQL is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for Redis
echo ""
echo "Waiting for Redis to be ready..."
for i in {1..30}; do
    if docker exec salesagent-redis redis-cli ping > /dev/null 2>&1; then
        echo "鉁?Redis is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head
echo "鉁?Migrations completed"

# Create MinIO bucket
echo ""
echo "Setting up MinIO..."
docker exec salesagent-minio mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
docker exec salesagent-minio mc mb local/salesagent 2>/dev/null || echo "Bucket already exists"
echo "鉁?MinIO configured"

# Verify installation
echo ""
echo "Running verification checks..."
python scripts/verify_phase1.py

echo ""
echo "=========================================="
echo "鉁?Phase 1 Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API keys"
echo "  2. Start API: uvicorn salesagent.main:app --reload"
echo "  3. Start WeChat Bot: python scripts/run_wechat_personal.py"
echo "  4. Visit: http://localhost:8000/docs"
echo ""
echo "To stop services: docker-compose -f docker-compose.dev.yml down"
echo "=========================================="
