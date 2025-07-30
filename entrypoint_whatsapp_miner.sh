#!/bin/bash

set -e

APP_FILE="/app/src/receive_notification.py"
#APP_FILE="/app/src/docker_debug.py"

echo "Entrypoint script executing"

if [[ ! -f "$APP_FILE" ]]; then
	echo "❌ ERROR: $APP_FILE not found! Exiting."
	exit 1
fi

echo "Current working dir: $(pwd)"
echo "List /app/src:"
ls -l /app/src

python -u "$APP_FILE"
