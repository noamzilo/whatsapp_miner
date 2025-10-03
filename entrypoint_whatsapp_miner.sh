#!/usr/bin/env bash
# entrypoint_whatsapp_miner.sh
# Entrypoint for WhatsApp Miner service (message receiver)

set -euo pipefail

echo "🚀 Starting WhatsApp Miner (message receiver)..."
echo "🌍 Environment: ${ENV_NAME:-dev}"

# Change to app directory
cd /app

# Run the miner application
exec python -u /app/src/message_mining/receive_notification.py
