# Production Dockerfile for BHIMA Earth System Intelligence API (Google Cloud Run)
FROM python:3.12-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/

# Copy preprocessed observations database and persistent data
# This allows Cloud Run containers to serve all 72 months of real NASA observations instantly (<10ms)
COPY data/ ./data/

# Copy documentation and metadata
COPY README.md* ./

# Ensure data directory permissions
RUN mkdir -p /app/data/storage /app/data/raw_parquet

# Cloud Run binds to $PORT dynamically (default 8080)
EXPOSE 8080

# Production startup using uvicorn binding to 0.0.0.0 and PORT
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2 --timeout-keep-alive 65
