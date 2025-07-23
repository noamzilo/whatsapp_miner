#!/bin/bash

set -e

APP_FILE="/app/src/receive_notification.py"

echo "Entrypoint script executing"

if [[ ! -f "$APP_FILE" ]]; then
	echo "❌ ERROR: $APP_FILE not found! Exiting."
	exit 1
fi

python "$APP_FILE"
