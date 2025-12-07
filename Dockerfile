FROM python:3.11-slim-bookworm

# Install ffmpeg and dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app directory
WORKDIR /app

# Copy application files
COPY main.py .
COPY docker-healthcheck.sh /usr/local/bin/healthcheck.sh

# Make healthcheck executable
RUN chmod +x /usr/local/bin/healthcheck.sh

# Create necessary directories
RUN mkdir -p /app/.progress /app/files/raw /app/files/public

# Setup cron job (runs every hour by default)
# The cron schedule can be overridden via environment variable
RUN echo "0 * * * * cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/video-converter && \
    chmod 0644 /etc/cron.d/video-converter && \
    crontab /etc/cron.d/video-converter && \
    touch /var/log/cron.log

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "================================="\n\
echo "Video Converter - Starting"\n\
echo "================================="\n\
\n\
# Display configuration\n\
echo "Configuration:"\n\
echo "  RAW_DIR: /app/files/raw"\n\
echo "  PUBLIC_DIR: /app/files/public"\n\
echo "  CRON_SCHEDULE: ${CRON_SCHEDULE:-0 * * * *}"\n\
echo "  RUN_ON_START: ${RUN_ON_START:-true}"\n\
echo ""\n\
\n\
# Update cron schedule if CRON_SCHEDULE is set\n\
if [ -n "$CRON_SCHEDULE" ]; then\n\
    echo "$CRON_SCHEDULE cd /app && /usr/local/bin/python main.py >> /var/log/cron.log 2>&1" > /etc/cron.d/video-converter\n\
    chmod 0644 /etc/cron.d/video-converter\n\
    crontab /etc/cron.d/video-converter\n\
    echo "Cron schedule configured: $CRON_SCHEDULE"\n\
else\n\
    echo "Using default cron schedule: 0 * * * * (every hour)"\n\
fi\n\
echo ""\n\
\n\
# Check if directories are mounted and accessible\n\
if [ ! -d /app/files/raw ] || [ -z "$(ls -A /app/files/raw 2>/dev/null)" ]; then\n\
    echo "WARNING: RAW directory is empty or not mounted properly"\n\
    echo "Please check your volume configuration in compose.yaml"\n\
fi\n\
\n\
if [ ! -d /app/files/public ]; then\n\
    echo "WARNING: PUBLIC directory not mounted properly"\n\
    mkdir -p /app/files/public\n\
fi\n\
\n\
# Run initial sync if requested\n\
if [ "$RUN_ON_START" = "true" ]; then\n\
    echo "================================="\n\
    echo "Running initial sync..."\n\
    echo "================================="\n\
    python main.py || echo "Initial sync completed with errors"\n\
    echo ""\n\
fi\n\
\n\
# Start cron in foreground\n\
echo "================================="\n\
echo "Starting cron daemon..."\n\
echo "Next scheduled run: $(date -d \"$(echo $CRON_SCHEDULE | awk '\''{print $2\":\"$1}'\\'')\" +\"%H:%M\" 2>/dev/null || echo \"check cron schedule\")"\n\
echo "Logs: /var/log/cron.log and /app/sync.log"\n\
echo "================================="\n\
echo ""\n\
\n\
# Start cron and tail logs\n\
cron && tail -f /var/log/cron.log /app/sync.log\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Health check using custom script
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/entrypoint.sh"]
