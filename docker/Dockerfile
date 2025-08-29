# Multi-stage Docker build for Router Manager with nginx proxy support

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    nginx-light \
    certbot \
    openssl \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p \
    /var/log/router-manager \
    /var/log/nginx \
    /var/www/certbot \
    /etc/nginx/sites-available \
    /etc/nginx/sites-enabled \
    /app/media \
    /app/staticfiles

# Set proper permissions
RUN chown -R app:app /app /var/log/router-manager /var/www/certbot
RUN chmod +x /app/docker/entrypoint.sh

# Switch to app user
USER app

# Set PATH for local binaries
ENV PATH=/home/app/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=router_manager.settings

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Entry point
ENTRYPOINT ["/app/docker/entrypoint.sh"]