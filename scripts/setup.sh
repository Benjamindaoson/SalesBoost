#!/bin/bash

# SalesBoost Setup Script
# This script sets up the development environment

set -e

echo "================================"
echo "SalesBoost Setup"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Warning: Docker is not installed. Some features may not work."
fi

echo "✓ Prerequisites check passed"
echo ""

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..
echo "✓ Backend dependencies installed"
echo ""

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..
echo "✓ Frontend dependencies installed"
echo ""

# Create .env files if they don't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env 2>/dev/null || echo "Warning: .env.example not found"
fi

if [ ! -f backend/.env ]; then
    echo "Creating backend/.env file..."
    cp backend/.env.example backend/.env 2>/dev/null || echo "Warning: backend/.env.example not found"
fi

if [ ! -f frontend/.env ]; then
    echo "Creating frontend/.env file..."
    cp frontend/.env.example frontend/.env 2>/dev/null || echo "Warning: frontend/.env.example not found"
fi

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Configure your .env files"
echo "  2. Run 'make dev' to start the development environment"
echo "  3. Visit http://localhost:8000 for the backend API"
echo "  4. Visit http://localhost:5173 for the frontend"
echo ""
