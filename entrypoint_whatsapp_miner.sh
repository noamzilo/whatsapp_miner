#!/usr/bin/env bash
# entrypoint_whatsapp_miner.sh
# Environment-aware entrypoint for WhatsApp Miner containers
# Routes to either sniffer or classifier based on DATABASE_ENV

set -euo pipefail

echo "🚀 Starting WhatsApp Miner container..."

# Get environment (default to dev)
DATABASE_ENV="${DATABASE_ENV:-dev}"
echo "🌍 Environment: $DATABASE_ENV"

# Determine which service to run based on environment
case "$DATABASE_ENV" in
    "dev"|"prd")
        echo "🤖 Starting message classifier for environment: $DATABASE_ENV"
        APP_FILE="/app/src/message_classification/classify_new_messages.py"
        ;;
    *)
        echo "📡 Starting WhatsApp sniffer"
        APP_FILE="/app/src/receive_notification.py"
        ;;
esac

echo "📁 Running: $APP_FILE"

# Change to app directory
cd /app

# Run the application
python -u "$APP_FILE"
