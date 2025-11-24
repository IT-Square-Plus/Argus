# Multi-stage Dockerfile for Argus MCP Server
# Stage 1: Build stage
FROM python:3.13-slim AS builder

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy package files (required for version resolution)
COPY pyproject.toml ./
COPY src/ ./src/

# Install package in editable mode (makes version metadata available)
RUN uv pip install --system -e .

# Stage 2: Runtime stage
FROM python:3.13-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages and metadata from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (installed as editable package)
COPY --from=builder /app/src /app/src

# Expose port 8081
EXPOSE 8081

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the MCP server
CMD ["python", "-m", "src.server"]
