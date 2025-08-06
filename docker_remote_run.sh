#!/usr/bin/env bash
# docker_remote_run.sh
# Runs on EC2; forwards to docker_run_core.sh.

set -euo pipefail

: "${ENV_FILE:?}"  # passed in by docker_run.sh --remote
: "${ENVIRONMENT:-dev}"  # passed in by docker_run.sh --remote

# ── Load every secret from the Doppler .env file ───────────────────────────
set -a
source "$ENV_FILE"
set +a

# Map Doppler creds (now present in ENV_FILE) to standard AWS vars
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

# Pass NEW_IMAGE_DIGEST to docker_run_core.sh if available
if [[ -n "${DIGEST_FILE_PATH:-}" ]]; then
    export DIGEST_FILE_PATH
fi

# Pass ENVIRONMENT and ENV_NAME to docker_run_core.sh
export ENVIRONMENT
export ENV_NAME="$ENVIRONMENT"

# Remove quotes from ENV_NAME if present
ENV_NAME="${ENV_NAME%\"}"
ENV_NAME="${ENV_NAME#\"}"

# Pass ENV_FILE to docker_run_core.sh
export ENV_FILE

echo "🌍 Environment: $ENVIRONMENT"
echo "🏷️  Env Name: $ENV_NAME"
echo "📄 Env File: $ENV_FILE"

./docker_run_core.sh

# Clean up digest file if it exists
if [[ -n "${DIGEST_FILE_PATH:-}" && -f "$DIGEST_FILE_PATH" ]]; then
    rm -f "$DIGEST_FILE_PATH"
fi

echo "✅ Remote deployment completed"
