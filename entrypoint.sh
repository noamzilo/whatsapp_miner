#!/bin/bash

set -e

# Optional: activate doppler here if needed (but you said it's injected at runtime already)

# Run your app (adjust path if your main file is not in src/)
python src/receive_notification.py
