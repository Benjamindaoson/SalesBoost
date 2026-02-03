#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic -c config/database/alembic.ini upgrade head

# Start application
echo "Starting SalesBoost API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
