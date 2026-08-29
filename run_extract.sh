#!/bin/bash
LOG="/home/vboxuser/agenda/cron.log"
{
    echo "=== \$(date '+%Y-%m-%d %H:%M:%S') - Starting agenda extraction ==="
    source /home/vboxuser/.hermes/venv/bin/activate
    if python /home/vboxuser/agenda/extract_details.py; then
        echo "=== \$(date '+%Y-%m-%d %H:%M:%S') - Extraction completed successfully ==="
    else
        echo "=== \$(date '+%Y-%m-%d %H:%M:%S') - Extraction FAILED with exit code \$? ==="
    fi
    deactivate
    echo "=== \$(date '+%Y-%m-%d %H:%M:%S') - End of run ==="
} >> "$LOG"