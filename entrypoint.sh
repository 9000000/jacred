#!/bin/sh
set -eu

cleanup() {
    echo "Received signal, shutting down gracefully..."
    exit 0
}
trap cleanup TERM INT

# Config priority: init.yaml > init.conf (same as application)
if [ -f /app/config/init.yaml ]; then
    echo "Using existing configuration (init.yaml)..."
    cp /app/config/init.yaml /app/init.yaml
    chmod 640 /app/init.yaml
    rm -f /app/init.conf
elif [ -f /app/config/init.conf ]; then
    echo "Using existing configuration (init.conf)..."
    cp /app/config/init.conf /app/init.conf
    chmod 640 /app/init.conf
    rm -f /app/init.yaml
else
    echo "Initializing configuration..."
    if [ -f /app/defaults/init.yaml ]; then
        cp /app/defaults/init.yaml /app/config/init.yaml
        cp /app/defaults/init.yaml /app/init.yaml
        chmod 640 /app/config/init.yaml /app/init.yaml
        rm -f /app/init.conf
    else
        cp /app/defaults/init.conf /app/config/init.conf
        cp /app/defaults/init.conf /app/init.conf
        chmod 640 /app/config/init.conf /app/init.conf
        rm -f /app/init.yaml
    fi
fi

if [ ! -r /app/init.yaml ] && [ ! -r /app/init.conf ]; then
    echo "ERROR: Cannot read configuration file (init.yaml or init.conf)" >&2
    exit 1
fi

if [ ! -x /app/JacRed ]; then
    echo "ERROR: Application binary is not executable" >&2
    exit 1
fi

# Copy default Data files if missing (volume mount overwrites built-in files)
if [ -d /app/defaults ]; then
    for f in crontab example.yaml example.conf; do
        if [ -f /app/defaults/$f ] && [ ! -f /app/Data/$f ]; then
            echo "Restoring default Data/$f from defaults..."
            cp /app/defaults/$f /app/Data/$f
        fi
    done
fi

# Fix permissions for Data, config directories and config files
echo "Fixing permissions..."
chown -R jacred:jacred /app/Data /app/config
chown jacred:jacred /app/init.yaml /app/init.conf 2>/dev/null || true

# Setup and start Cron
if [ -f /app/Data/crontab ]; then
    echo "Installing crontab..."
    mkdir -p /var/spool/cron/crontabs
    # Strip Windows CR and ensure trailing newline (required by crond)
    sed 's/\r$//' /app/Data/crontab > /var/spool/cron/crontabs/root
    echo "" >> /var/spool/cron/crontabs/root
    # Alpine crond requires crontab files owned by root:root with 600 perms
    chmod 600 /var/spool/cron/crontabs/root
    chown root:root /var/spool/cron/crontabs/root
    echo "Starting crond..."
    crond -b -l 2 -L /dev/stdout
    echo "Cron installed successfully. Verifying..."
    cat /var/spool/cron/crontabs/root | head -5
else
    echo "WARNING: No crontab found at /app/Data/crontab - cron parsing disabled!"
fi

# Start JacRed
echo "Starting Jacred (version: ${JACRED_VERSION:-unknown}) on $(date)"
echo "Architecture: $(uname -m)"
echo "User before drop: $(id)"

exec su-exec jacred "$@"
