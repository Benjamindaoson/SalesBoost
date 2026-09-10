#!/bin/bash
# SalesAgent V3 Development Environment Setup Script

set -e

echo "馃殌 SalesAgent V3 Development Environment Setup"
echo "================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}鉂?Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}鉁?Docker is running${NC}"

# Start infrastructure services
echo ""
echo "馃摝 Starting infrastructure services (PostgreSQL, Redis, MinIO)..."
docker-compose -f docker-compose.dev.yml up -d postgres redis minio

# Wait for PostgreSQL to be ready
echo ""
echo "鈴?Waiting for PostgreSQL to be ready..."
until docker exec salesagent-postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}鉁?PostgreSQL is ready${NC}"

# Wait for Redis to be ready
echo ""
echo "鈴?Waiting for Redis to be ready..."
until docker exec salesagent-redis redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}鉁?Redis is ready${NC}"

# Run database migrations
echo ""
echo "馃攧 Running database migrations..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

alembic upgrade head
echo -e "${GREEN}鉁?Database migrations completed${NC}"

# Create MinIO bucket
echo ""
echo "馃搧 Creating MinIO bucket..."
docker exec salesagent-minio mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
docker exec salesagent-minio mc mb local/salesagent 2>/dev/null || echo "Bucket already exists"
echo -e "${GREEN}鉁?MinIO bucket ready${NC}"

# Start observability stack (optional)
read -p "Start observability stack (Prometheus, Grafana, Jaeger)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "馃搳 Starting observability stack..."
    docker-compose -f docker-compose.dev.yml up -d prometheus grafana jaeger
    echo -e "${GREEN}鉁?Observability stack started${NC}"
    echo ""
    echo "Access URLs:"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3001 (admin/admin)"
    echo "  - Jaeger: http://localhost:16686"
fi

# Summary
echo ""
echo "================================================"
echo -e "${GREEN}鉁?Development environment is ready!${NC}"
echo ""
echo "Services running:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - MinIO: localhost:9000 (Console: localhost:9001)"
echo ""
echo "Next steps:"
echo "  1. Update .env file with your API keys"
echo "  2. Run: uvicorn salesagent.main:app --reload"
echo "  3. Visit: http://localhost:8000/docs"
echo ""
echo "To stop services: docker-compose -f docker-compose.dev.yml down"
echo "================================================"
