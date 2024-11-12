#!/bin/bash

# Ensure correct working directory
cd /app

# Start the cron service
service cron start

# Run the script once at startup
python3 /app/src/wsb.py

# Keep container running and monitor logs
exec tail -f /var/log/cron.log