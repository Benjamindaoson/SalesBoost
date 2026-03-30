#!/bin/bash

# SalesBoost Development Startup Script

set -e

echo "================================"
echo "Starting SalesBoost Development"
echo "================================"
echo ""

# Start Docker services
echo "Starting Docker services..."
docker-compose -f deployment/docker/compose.base.yml -f deployment/docker/compose.dev.yml up -d

echo "✓ Docker services started"
echo ""

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 5

# Start backend
echo "Starting backend server..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

echo "✓ Backend started (PID: $BACKEND_PID)"
echo ""

# Start frontend
echo "Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✓ Frontend started (PID: $FRONTEND_PID)"
echo ""

echo "================================"
echo "Development Environment Ready!"
echo "================================"
echo ""
echo "Services:"
echo "  Backend API:  http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  Frontend:     http://localhost:5173"
echo ""
echo "To stop services:"
echo "  - Press Ctrl+C"
echo "  - Run 'make docker-down'"
echo ""

# Wait for user interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose -f deployment/docker/compose.base.yml down; exit" INT TERM

wait
