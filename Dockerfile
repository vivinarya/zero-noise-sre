# Multi-stage production build for Zero-Noise SRE Core
FROM python:3.11-slim

WORKDIR /app

# Install git and system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy project files
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port (dynamic cloud port support)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

# Start the SRE Daemon & Web Cockpit
CMD ["sh", "-c", "python cmd/daemon/main.py --port ${PORT:-8000}"]
