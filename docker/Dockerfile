# Stage 1: Build stage
FROM --platform=linux/amd64 python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies (Debian-style)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /app/venv

# Copy requirements
COPY requirements.txt .
RUN /app/venv/bin/pip install --no-cache-dir --no-warn-script-location -r requirements.txt

# Stage 2: Runtime stage
FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

COPY --from=builder /app/venv /app/venv
COPY src/ ./src/
COPY config/.env.example ./config/
COPY docker/entrypoint.sh ./

# Set timezone to California (America/Los_Angeles)
ENV TZ=America/Los_Angeles

# Install runtime deps (Debian-style)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# User setup
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app && \
    sed -i 's/\r$//' /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENV PATH="/app/venv/bin:$PATH" \
    PYTHONPATH="/app/src:${PYTHONPATH:-}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser
ENTRYPOINT ["/app/entrypoint.sh"]
