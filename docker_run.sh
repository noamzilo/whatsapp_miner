#!/usr/bin/env bash
# Wrapper:
#   ./docker_run.sh            → local run
#   ./docker_run.sh --remote   → run on EC2

set -euo pipefail
MODE="${1:-local}"

# Map IAM → AWS CLI vars (already injected in CI or by wrapper)
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${DOCKER_CONTAINER_NAME_WHATSAPP_MINER:?}"
: "${AWS_EC2_REGION:?}"

IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
REGISTRY="${IMAGE_NAME%/*}"
LOGIN_PW=$(aws ecr get-login-password --region "$AWS_EC2_REGION")

if [[ "$MODE" == "--remote" || "$MODE" == "remote" ]]; then
	: "${AWS_EC2_HOST_ADDRESS:?}"
	: "${AWS_EC2_USERNAME:?}"
	: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
	: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"

	REMOTE_DIR="$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"

	# ── Prepare SSH key
	KEY_FILE=$(mktemp)
	echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
	chmod 400 "$KEY_FILE"

	# ── Ensure target dir exists
	ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no \
		"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" \
		"mkdir -p $REMOTE_DIR"

	# ── Ship helper script
	scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
		./docker_run_core.sh \
		"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/docker_run_core.sh"

	# ── Ship runtime env-file (all current env vars)
	ENV_TMP=$(mktemp)
	printenv > "$ENV_TMP"
	scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
		"$ENV_TMP" \
		"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/whatsapp_miner.env"
	rm -f "$ENV_TMP"

	# ── Execute helper on the remote box
	ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" bash -s <<REMOTE
set -euo pipefail
chmod +x "$REMOTE_DIR/docker_run_core.sh"
AWS_ECR_LOGIN_PASSWORD='$LOGIN_PW' \
AWS_ECR_REGISTRY='$REGISTRY' \
DOCKER_IMAGE_NAME_WHATSAPP_MINER='$IMAGE_NAME' \
DOCKER_CONTAINER_NAME_WHATSAPP_MINER='$DOCKER_CONTAINER_NAME_WHATSAPP_MINER' \
ENV_FILE='$REMOTE_DIR/whatsapp_miner.env' \
bash "$REMOTE_DIR/docker_run_core.sh"
REMOTE
	rm -f "$KEY_FILE"
else
	# ── Local run
	ENV_FILE=$(mktemp)
	printenv > "$ENV_FILE"

	AWS_ECR_LOGIN_PASSWORD="$LOGIN_PW" \
	AWS_ECR_REGISTRY="$REGISTRY" \
	DOCKER_IMAGE_NAME_WHATSAPP_MINER="$IMAGE_NAME" \
	DOCKER_CONTAINER_NAME_WHATSAPP_MINER="$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" \
	ENV_FILE="$ENV_FILE" \
	./docker_run_core.sh

	rm -f "$ENV_FILE"
fi
