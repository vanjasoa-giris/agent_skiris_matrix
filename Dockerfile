# Dockerfile for Elektra Agent Matrix
FROM python:3.11-slim

LABEL maintainer="DevOps Team" \
      description="Elektra Matrix Bot - AI Agent connecting Matrix to MCP" \
      version="2.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies for cryptography and matrix-nio
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
# We use --no-cache-dir to keep the image small
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (keep src directory)
COPY src/ src/

# Create a non-root user for security
RUN useradd -m -u 1000 elektra && \
    chown -R elektra:elektra /app

USER elektra

# Run as a module from the 'src' directory
CMD ["python", "-m", "src.main"]
