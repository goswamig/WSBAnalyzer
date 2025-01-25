FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/src /app/config

# Copy the entire src directory
COPY src/ /app/src/

# Copy configuration files
COPY config/.env.example /app/config/
COPY .env /app/

# Create log directory and file
RUN mkdir -p /var/log && \
    touch /var/log/cron.log && \
    chmod 0666 /var/log/cron.log

# Copy and setup entrypoint script
COPY docker/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Set Python path to include the src directory
ENV PYTHONPATH="/app/src:${PYTHONPATH:-}"

# Run the command on container startup
ENTRYPOINT ["/app/entrypoint.sh"]
