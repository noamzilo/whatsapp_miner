#!/usr/bin/env bash
# docker_run_with_doppler.sh
# Local entry: ensure Doppler, map AWS creds, generate temp .env, run core.

set -euo pipefail

# Source utility functions
source "$(dirname "$0")/docker_utils.sh"

cd "$(dirname "$0")"

# ── 1. Always re-exec inside a fresh Doppler context ────────────────────────
if [[ -z "${DOPPLER_REFRESHED:-}" ]]; then
    echo "🔄 Re-executing with fresh Doppler context..."
    export DOPPLER_REFRESHED=1
    exec doppler run --preserve-env -- "$0" "$@"
fi

# Unquote Doppler variables
unquote_doppler_vars

echo "✅ Running in Doppler context: $DOPPLER_PROJECT/$DOPPLER_CONFIG"
echo "🌍 Environment: ${ENV_NAME:-dev}"

# ── 2. Required Doppler keys must exist ─────────────────────────────────────
required_vars=(
	ENV_NAME
	DOCKER_IMAGE_NAME_WHATSAPP_MINER
    DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER
	AWS_EC2_REGION
	AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID
	AWS_IAM_WHATSAPP_MINER_ACCESS_KEY
)
for v in "${required_vars[@]}"; do
	if [[ -z "${!v:-}" ]]; then
		echo "❌ Missing required secret: $v"
		echo "Available variables:"
		env | grep -E "(AWS_|DOCKER_)" | sort || true
		exit 1
	fi
done

# ── 3. Map Doppler creds → AWS standard names ───────────────────────────────
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

echo "🔐 AWS credentials configured:"
echo "   Region: $AWS_DEFAULT_REGION"
echo "   Access Key ID: ${AWS_ACCESS_KEY_ID:0:8}..."
echo "   Secret Access Key: ${#AWS_SECRET_ACCESS_KEY} chars"

# ── 4. Test AWS credentials before proceeding ───────────────────────────────
echo "🧪 Testing AWS credentials..."
if ! aws sts get-caller-identity >/dev/null 2>&1; then
	echo "❌ AWS credentials are invalid or expired"
	echo "Caller identity test failed"
	exit 1
fi
echo "✅ AWS credentials are valid"

# ── 5. Generate temp .env containing ALL Doppler secrets ────────────────────
ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"' EXIT INT TERM
echo "📝 Generating environment file: $ENV_FILE"
doppler secrets download --no-file --format docker > "$ENV_FILE"
export ENV_FILE    # read by docker-compose.yml

# ── 6. Delegate to core runner ──────────────────────────────────────────────
echo "🚀 Starting docker core runner..."
./docker_run_core.sh --env "${ENV_NAME:-dev}"
