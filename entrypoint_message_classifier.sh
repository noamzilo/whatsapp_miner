#!/bin/bash

set -e

APP_FILE="/app/src/message_classification/classify_new_messages.py"

echo "Entrypoint script executing for Message Classifier"

if [[ ! -f "$APP_FILE" ]]; then
	echo "❌ ERROR: $APP_FILE not found! Exiting."
	exit 1
fi

echo "Current working dir: $(pwd)"
echo "List /app/src:"
ls -l /app/src

python -u "$APP_FILE" 