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
    
    # Determine target times
    if [ "$current_day" = "Sat" ] || [ "$current_day" = "Sun" ]; then
        targets="11:00 20:00"  # No arrays - use space-separated string
    else
        targets="06:25 09:25 12:25 17:00 21:00"
    fi

    next_run_epoch=""
    for target in $targets; do
        target_epoch=$(date -d "$target" +%s 2>/dev/null)
        if [ -n "$target_epoch" ] && [ "$target_epoch" -gt "$current_epoch" ]; then
            if [ -z "$next_run_epoch" ] || [ "$target_epoch" -lt "$next_run_epoch" ]; then
                next_run_epoch=$target_epoch
            fi
        fi
    done

    if [ -z "$next_run_epoch" ]; then
        days_to_add=1
        while true; do
            next_day_epoch=$((current_epoch + days_to_add * 86400))
            next_day=$(date -d "@$next_day_epoch" +%a)
            
            if [ "$next_day" = "Sat" ] || [ "$next_day" = "Sun" ]; then
                next_targets="11:00 20:00"
            else
                next_targets="06:25 09:25 12:25 17:00 21:00"
            fi
            
            first_target=$(echo "$next_targets" | awk '{print $1}')
            next_run_epoch=$(date -d "@$next_day_epoch $first_target" +%s 2>/dev/null)
            
            if [ -n "$next_run_epoch" ] && [ "$next_run_epoch" -gt "$current_epoch" ]; then
                break
            fi
            days_to_add=$((days_to_add + 1))
        done
    fi

    sleep_seconds=$((next_run_epoch - current_epoch))
    next_run_time=$(date -d "@$next_run_epoch")
    
    echo "$(date) - Next analysis scheduled for: $next_run_time" | tee -a /var/log/cron.log
    echo "$(date) - Sleeping for $sleep_seconds seconds" | tee -a /var/log/cron.log
    
    sleep $sleep_seconds
    run_script
done
