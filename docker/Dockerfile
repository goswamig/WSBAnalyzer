# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install cron and required system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/src /app/config

# Copy the source code and configuration
COPY src/wsb.py /app/src/
COPY config/.env.example /app/config/
COPY .env /app/

# Setup cron job
COPY docker/crontab /etc/cron.d/wsb-cron
RUN chmod 0644 /etc/cron.d/wsb-cron && \
    crontab /etc/cron.d/wsb-cron

# Create log directory and file
RUN mkdir -p /var/log && \
    touch /var/log/cron.log && \
    chmod 0666 /var/log/cron.log

# Copy and setup entrypoint script
COPY docker/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Run the command on container startup
ENTRYPOINT ["/app/entrypoint.sh"]