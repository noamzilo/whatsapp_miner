#!/bin/bash

set -e

echo "🚀 Entrypoint script executing"

# Determine which service to run based on DATABASE_ENV
DATABASE_ENV="${DATABASE_ENV:-dev}"
echo "🌍 Environment: $DATABASE_ENV"

case "$DATABASE_ENV" in
    "dev"|"prd")
        echo "🤖 Starting message classifier for environment: $DATABASE_ENV"
        APP_FILE="/app/src/message_classification/classify_messages_from_queue.py"
        ;;
    *)
        echo "📡 Starting WhatsApp sniffer"
        APP_FILE="/app/src/receive_notification.py"
        ;;
esac

if [[ ! -f "$APP_FILE" ]]; then
    echo "❌ ERROR: $APP_FILE not found! Exiting."
    exit 1
fi

echo "📁 Current working dir: $(pwd)"
echo "📂 List /app/src:"
ls -l /app/src

echo "🚀 Starting: $APP_FILE"
python -u "$APP_FILE"
