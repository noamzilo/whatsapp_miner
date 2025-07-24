#!/usr/bin/env bash
set -euo pipefail

# ── Load Doppler secrets
eval "$(doppler secrets download --no-file --format env)"

: "${AWS_EC2_HOST_ADDRESS:?}"
: "${AWS_EC2_USERNAME:?}"
: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"

# ── Prepare SSH key
KEY_FILE=$(mktemp)
echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
chmod 400 "$KEY_FILE"

# ── Ensure remote dir exists
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no \
	"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" \
	"mkdir -p $AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"

# ── Upload core runner
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
	docker_run_core.sh \
	"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER/docker_run_core.sh"

# ── Upload env file
ENV_FILE=$(mktemp)
doppler secrets download --no-file --format docker > "$ENV_FILE"
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
	"$ENV_FILE" \
	"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER/whatsapp_miner.env"
rm -f "$ENV_FILE"
rm -f "$KEY_FILE"

echo "✅ Upload complete."
