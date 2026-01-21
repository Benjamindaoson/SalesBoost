FROM python:3.10-slim

# Install system dependencies
# gcc and libpq-dev are required for psycopg2 (PostgreSQL driver)
# curl is useful for health checks
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Start command
CMD ["./start.sh"]
