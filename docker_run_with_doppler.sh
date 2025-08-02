#!/usr/bin/env bash
# docker_run_with_doppler.sh
# Local entry: ensure Doppler, map AWS creds, generate temp .env, run core.

set -euo pipefail

# ── 1. Re-exec inside Doppler if not already ────────────────────────────────
if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
	exec doppler run --project whatsapp_miner_backend --config dev_personal --preserve-env -- "$0" "$@"
fi

# ── 2. Required Doppler keys must exist ─────────────────────────────────────
required_vars=(
	DOCKER_IMAGE_NAME_WHATSAPP_MINER
	AWS_EC2_REGION
	AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID
	AWS_IAM_WHATSAPP_MINER_ACCESS_KEY
)
for v in "${required_vars[@]}"; do
	[[ -z "${!v:-}" ]] && { echo "❌ Missing required secret: $v"; exit 1; }
done

# ── 3. Map Doppler creds → AWS standard names (core functionality restored) ─
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"        # convenience for AWS CLI

# ── 4. Prepare ECR login vars ───────────────────────────────────────────────
IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
AWS_ECR_REGISTRY="${IMAGE_NAME%/*}"
AWS_ECR_LOGIN_PASSWORD="$(aws ecr get-login-password --region "$AWS_EC2_REGION")"
export AWS_ECR_REGISTRY AWS_ECR_LOGIN_PASSWORD

# ── 5. Generate temp .env containing ALL Doppler secrets ────────────────────
ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"' EXIT INT TERM
doppler secrets download --no-file --format docker > "$ENV_FILE"
export ENV_FILE    # read by docker-compose.yml

# ── 6. Delegate to core runner ──────────────────────────────────────────────
./docker_run_core.sh
