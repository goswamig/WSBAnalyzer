#!/bin/bash

# Debug output
echo "Starting entrypoint.sh..."
pwd
ls -la /app
ls -la /app/src

# Ensure correct working directory
cd /app

# Function to run the script and log output
run_script() {
    echo "$(date) - Starting WSB analysis..." | tee -a /var/log/cron.log
    echo "Python path: $PYTHONPATH" | tee -a /var/log/cron.log
    echo "Current directory: $(pwd)" | tee -a /var/log/cron.log
    python3 -c "import sys; print(sys.path)" | tee -a /var/log/cron.log
    python3 /app/src/wsb.py 2>&1 | tee -a /var/log/cron.log
    echo "$(date) - Finished WSB analysis" | tee -a /var/log/cron.log
}

# Run script immediately on startup
run_script

# Then run every hour
while true; do
    echo "Sleeping for 1 hour..." | tee -a /var/log/cron.log
    sleep 3600
    run_script
done