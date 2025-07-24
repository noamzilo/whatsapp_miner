#!/bin/bash
# Entry-point wrapper.
#   ./docker_run.sh            → local   run
#   ./docker_run.sh --remote   → run on EC2

set -euo pipefail
MODE="${1:-local}"

# ── Load all secrets into env
eval "$(doppler secrets download --no-file --format env)"

# Map IAM → AWS CLI vars  ▼▼  (add these two lines)
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${DOCKER_CONTAINER_NAME_WHATSAPP_MINER:?}"
: "${AWS_EC2_REGION:?}"
: "${AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID:?}"
: "${AWS_IAM_WHATSAPP_MINER_ACCESS_KEY:?}"

IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
REGISTRY="${IMAGE_NAME%/*}"
LOGIN_PW=$(aws ecr get-login-password --region "$AWS_EC2_REGION")

if [[ "$MODE" == "--remote" || "$MODE" == "remote" ]]; then
	: "${AWS_EC2_HOST_ADDRESS:?}"
	: "${AWS_EC2_USERNAME:?}"
	: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
	: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"

	# ── prepare SSH key
	KEY_FILE=$(mktemp)
	echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d >"$KEY_FILE"
	chmod 400 "$KEY_FILE"

	# ── copy core script + env file
	ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no \
		"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" \
		"mkdir -p '$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER'"

	scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
		./docker_run_core.sh \
		"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER/"

	ENV_TMP=$(mktemp)
	doppler secrets download --no-file --format docker >"$ENV_TMP"
	scp -i "$KEY_FILE" -o StrictHostKeyChecking=no \
		"$ENV_TMP" \
		"$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER/whatsapp_miner.env"
	rm "$ENV_TMP"

	# ── execute remotely
	ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" <<REMOTE
		set -euo pipefail
		cd "$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"
		chmod +x docker_run_core.sh
		AWS_ECR_LOGIN_PASSWORD='$LOGIN_PW' \
		AWS_ECR_REGISTRY='$REGISTRY' \
		DOCKER_IMAGE_NAME_WHATSAPP_MINER='$IMAGE_NAME' \
		DOCKER_CONTAINER_NAME_WHATSAPP_MINER='$DOCKER_CONTAINER_NAME_WHATSAPP_MINER' \
		ENV_FILE='./whatsapp_miner.env' \
		bash ./docker_run_core.sh
REMOTE
	rm "$KEY_FILE"
else
	# ── local run
	ENV_FILE=$(mktemp)
	doppler secrets download --no-file --format docker >"$ENV_FILE"

	AWS_ECR_LOGIN_PASSWORD="$LOGIN_PW" \
	AWS_ECR_REGISTRY="$REGISTRY" \
	DOCKER_IMAGE_NAME_WHATSAPP_MINER="$IMAGE_NAME" \
	DOCKER_CONTAINER_NAME_WHATSAPP_MINER="$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" \
	ENV_FILE="$ENV_FILE" \
	./docker_run_core.sh

	rm "$ENV_FILE"
fi
