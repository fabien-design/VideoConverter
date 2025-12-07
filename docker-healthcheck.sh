#!/bin/bash
# Docker healthcheck script

# Check if lock file is older than 24 hours
if [ -f /app/.sync.lock ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -c %Y /app/.sync.lock) ))
    if [ $LOCK_AGE -gt 86400 ]; then
        echo "Lock file is stale (older than 24h)"
        exit 1
    fi
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "Python not found"
    exit 1
fi

# Check if ffmpeg is available
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found"
    exit 1
fi

# Check if directories are mounted
if [ ! -d /app/files/raw ]; then
    echo "RAW directory not mounted"
    exit 1
fi

if [ ! -d /app/files/public ]; then
    echo "PUBLIC directory not mounted"
    exit 1
fi

exit 0
