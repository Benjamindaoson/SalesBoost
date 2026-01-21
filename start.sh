#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Checking if data ingestion is needed..."
# Check if vector DB is empty (simplified check or just run ingestion if needed)
# For now, we'll run a safe ingestion script if provided, or skip.
# Ideally, we should check if data exists.
# But simply running ingestion might be safe if it's idempotent or we accept overwrite.
# Let's assume we run it on demand via a separate job or manually for now to save startup time, 
# OR we can add a flag ENV_RUN_SEED=true

if [ "$ENV_RUN_SEED" = "true" ]; then
    echo "Running data ingestion..."
    python scripts/ingest_sales_data_robust.py
fi

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
