# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with cache
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_CACHE_DIR=/root/.cache/pip
COPY config/python/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Pre-download models to cache
COPY scripts/download_models.py scripts/
ENV SENTENCE_TRANSFORMERS_HOME=/app/models_cache
RUN python scripts/download_models.py

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime libs if needed (e.g. for sqlite)
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy cached models
COPY --from=builder /app/models_cache /app/models_cache
ENV SENTENCE_TRANSFORMERS_HOME=/app/models_cache

# Copy application code
COPY . .

# Environment setup
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2} --timeout-keep-alive 65 --proxy-headers --forwarded-allow-ips=*"]
