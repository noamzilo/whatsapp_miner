#!/usr/bin/env bash
# entrypoint_message_classifier.sh
# Entrypoint for Message Classifier service

set -euo pipefail

echo "🚀 Starting Message Classifier service..."
echo "🌍 Environment: ${ENV_NAME:-dev}"

# Change to app directory
cd /app

# Run the classifier application
exec python -u /app/src/message_classification/classify_new_messages.py 