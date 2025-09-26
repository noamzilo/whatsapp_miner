#!/usr/bin/env bash
# docker_remote_run.sh
# Runs on EC2; forwards to docker_run_core.sh.

set -euo pipefail

: "${SECRETS_B64:?}"   # passed in by docker_run.sh --remote
: "${ENVIRONMENT:-dev}"

# Decode the secrets bundle into a temp JSON, then render a docker-format env file
tmp_json="$(mktemp)"
trap 'rm -f "$tmp_json" "$ENV_FILE"' EXIT INT TERM
printf '%s' "$SECRETS_B64" | base64 -d > "$tmp_json"

# Create an ephemeral env file for docker-compose (env_file requires a path)
ENV_FILE="/tmp/whatsapp_miner.$$.env"

# Prefer jq; if unavailable, fall back to python3
if command -v jq >/dev/null 2>&1; then
  jq -r 'to_entries[] | "\(.key)=\(.value|tostring)"' "$tmp_json" > "$ENV_FILE"
elif command -v python3 >/dev/null 2>&1; then
  export tmp_json ENV_FILE
  python3 - << 'PY'
import json, os, sys
tmp = os.environ.get('tmp_json')
out = os.environ.get('ENV_FILE')
with open(tmp, 'r') as f:
    data = json.load(f)
with open(out, 'w') as f:
    for k, v in data.items():
        f.write(f"{k}={str(v)}\n")
PY
else
  echo "❌ Neither jq nor python3 is available on the remote host to decode SECRETS_B64"
  exit 1
fi

# Load env into this shell for AWS/ECR and script needs
set -a
source "$ENV_FILE"
set +a

# Map Doppler-style creds (now present) to standard AWS vars
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

# Forward optional digest file path and environment naming
if [[ -n "${DIGEST_FILE_PATH:-}" ]]; then
    export DIGEST_FILE_PATH
fi
export ENVIRONMENT
export ENV_NAME="$ENVIRONMENT"
ENV_NAME="${ENV_NAME%\"}"
ENV_NAME="${ENV_NAME#\"}"
export ENV_FILE

echo "🌍 Environment: $ENVIRONMENT"
echo "🏷️  Env Name: $ENV_NAME"
echo "📄 Env File: $ENV_FILE"

# Debug: Check user and AWS environment
echo "🔍 Debug: Current user: $(whoami)"
echo "🔍 Debug: AWS_ACCESS_KEY_ID length: ${#AWS_ACCESS_KEY_ID}"
echo "🔍 Debug: AWS_SECRET_ACCESS_KEY length: ${#AWS_SECRET_ACCESS_KEY}"
echo "🔍 Debug: AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION"

./docker_run_core.sh

# Clean up digest file if it exists (do not mask exit codes; handled by trap for env/json)
if [[ -n "${DIGEST_FILE_PATH:-}" && -f "$DIGEST_FILE_PATH" ]]; then
    rm -f "$DIGEST_FILE_PATH"
fi

echo "✅ Remote deployment completed"
