#!/usr/bin/env bash
# entrypoint_whatsapp_miner.sh
# Entrypoint for WhatsApp Miner service (message receiver)

set -euo pipefail

echo "🚀 Starting WhatsApp Miner (message receiver)..."
echo "🌍 Environment: ${ENV_NAME:-dev}"

# Change to app directory
cd /app

# Start SSH server in background for PyCharm remote development
if [ "${ENV_NAME:-dev}" = "dev" ]; then
    echo "🔐 Starting SSH server for PyCharm remote development..."
    /usr/sbin/sshd -D &
    echo "✓ SSH server started on port 2222"
fi

# Run the miner application
exec python -u /app/src/message_mining/receive_notification.py
