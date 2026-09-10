# ── Multi-stage Dockerfile for SalesAgent V3 ────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 salesagent && \
    chown -R salesagent:salesagent /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/salesagent/.local

# Copy application code
COPY --chown=salesagent:salesagent . .

# Set PATH for user-installed packages
ENV PATH=/home/salesagent/.local/bin:$PATH

# Switch to non-root user
USER salesagent

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "salesagent.main:app", "--host", "0.0.0.0", "--port", "8000"]
