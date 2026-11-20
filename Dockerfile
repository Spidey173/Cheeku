# Multi-stage lean container for Cheeku AI Voice OS Core
FROM python:3.11-slim

LABEL maintainer="Cheeku AI Team"
LABEL description="Cheeku AI Voice OS Core - Headless Server & Neural HUD"

# Set environment defaults: unbuffered output, non-interactive apt, and container host binding
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    HOST=0.0.0.0 \
    PORT=8000 \
    ENABLE_SYSTEM_ACTIONS=false

# Install minimal runtime dependencies (curl for health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group
RUN groupadd -g 1000 cheeku && \
    useradd -u 1000 -g cheeku -m -s /bin/bash cheeku

# Set working directory
WORKDIR /app

# Copy dependency definition and install packages using layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-create data and log directories and set ownership for cheeku user
RUN mkdir -p /app/backend/data /app/backend/logs && \
    chown -R cheeku:cheeku /app

# Copy application source code and tests
COPY --chown=cheeku:cheeku backend/ /app/backend/
COPY --chown=cheeku:cheeku frontend/ /app/frontend/
COPY --chown=cheeku:cheeku tests/ /app/tests/
COPY --chown=cheeku:cheeku pytest.ini run.py /app/

# Switch to non-root user for defensive execution
USER cheeku

# Expose HTTP and WebSocket port
EXPOSE 8000

# Container healthcheck targeting the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch Cheeku server via Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

