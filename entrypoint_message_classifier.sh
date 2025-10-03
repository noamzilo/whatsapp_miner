#!/usr/bin/env bash
# entrypoint_message_classifier.sh
# Entrypoint for Message Classifier service

set -euo pipefail

echo "🚀 Starting Message Classifier service..."
echo "🌍 Environment: ${ENV_NAME:-dev}"

# Change to app directory
cd /app

# Start SSH server in background for PyCharm remote development
if [ "${ENV_NAME:-dev}" = "dev" ]; then
    echo "🔐 Starting SSH server for PyCharm remote development..."
    # Start SSH server in background and redirect output
    nohup /usr/sbin/sshd -D > /dev/null 2>&1 &
    # Wait a moment for SSH server to start
    sleep 2
    echo "✓ SSH server started on port 2222"
fi

# Run the classifier application
exec python -u /app/src/message_classification/classify_new_messages.py 