# Multi-stage build for Python application
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml .

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir netmiko>=4.7.0 requests>=2.34.2

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code with cache busting
COPY switch_health_dashboard.py .
COPY SwitchhealthStatuscheck.py .
COPY switch_models.py .
COPY switch_configs.py .
COPY switch_health_web ./switch_health_web
RUN touch /app/switch_health_web/index.html

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Expose the dashboard port
EXPOSE 8787

# Default to binding to all interfaces in container
ENV SWITCH_DASHBOARD_HOST=0.0.0.0
ENV SWITCH_DASHBOARD_PORT=8787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8787), timeout=5)" || exit 1

CMD ["python", "switch_health_dashboard.py"]
