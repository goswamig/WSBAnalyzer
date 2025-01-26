#!/bin/sh

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

# Initial run
run_script

# Continuous scheduling loop
while true; do
    current_day=$(date +%a)
    current_time=$(date +%H:%M)
    current_epoch=$(date +%s)
    
    # Debug: Log current time
    echo "$(date) - Current time: $current_day $current_time ($current_epoch)" | tee -a /var/log/cron.log
    
    # Determine target times
    if [ "$current_day" = "Sat" ] || [ "$current_day" = "Sun" ]; then
        targets="11:00 15:00 20:00"
    else
        targets="06:25 09:25 12:25 17:00 21:00"
    fi

    next_run_epoch=""
    for target in $targets; do
        # Use UTC time for calculations
        target_epoch=$(date -u -d "$target" +%s 2>/dev/null || date -j -f "%H:%M" "$target" +%s 2>/dev/null)
        
        if [ -n "$target_epoch" ]; then
            # Convert target to current timezone
            target_epoch=$(date -d "@$target_epoch" +%s)
            
            if [ "$target_epoch" -gt "$current_epoch" ]; then
                if [ -z "$next_run_epoch" ] || [ "$target_epoch" -lt "$next_run_epoch" ]; then
                    next_run_epoch=$target_epoch
                fi
            fi
        fi
    done

    # Fallback to next day if no targets found
    if [ -z "$next_run_epoch" ]; then
        echo "$(date) - No future targets found today, checking tomorrow..." | tee -a /var/log/cron.log
        next_run_epoch=$((current_epoch + 86400))  # Add 24 hours
        next_run_epoch=$(date -d "@$next_run_epoch" +%s)
    fi

    sleep_seconds=$((next_run_epoch - current_epoch))
    
    # Prevent negative sleep time
    if [ "$sleep_seconds" -lt 0 ]; then
        sleep_seconds=0
    fi

    next_run_time=$(date -d "@$next_run_epoch")
    
    echo "$(date) - Next analysis scheduled for: $next_run_time" | tee -a /var/log/cron.log
    echo "$(date) - Sleeping for $sleep_seconds seconds" | tee -a /var/log/cron.log
    
    sleep $sleep_seconds
    run_script
done
