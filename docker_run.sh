#!/usr/bin/env bash
# Wrapper:
#   ./docker_run.sh            → local run
#   ./docker_run.sh --remote   → run on EC2

set -euo pipefail
MODE="${1:-local}"

# ── Required env vars ────────────────────────────────────────────────────────
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${DOCKER_CONTAINER_NAME_WHATSAPP_MINER:?}"
: "${AWS_EC2_REGION:?}"
: "${AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID:?}"
: "${AWS_IAM_WHATSAPP_MINER_ACCESS_KEY:?}"

export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
REGISTRY="${IMAGE_NAME%/*}"
LOGIN_PW="$(aws ecr get-login-password --region "$AWS_EC2_REGION")"

# ── Local helper ─────────────────────────────────────────────────────────────
run_local() {
	ENV_FILE="$(mktemp)"
	printenv > "$ENV_FILE"

	AWS_ECR_LOGIN_PASSWORD="$LOGIN_PW" \
	AWS_ECR_REGISTRY="$REGISTRY" \
	DOCKER_IMAGE_NAME_WHATSAPP_MINER="$IMAGE_NAME" \
	DOCKER_CONTAINER_NAME_WHATSAPP_MINER="$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" \
	ENV_FILE="$ENV_FILE" \
	./docker_run_core.sh

	rm -f "$ENV_FILE"
	echo -e "\n🚀✅ Local container launched successfully ✅🚀\n"
}

# ── Remote helper ────────────────────────────────────────────────────────────
run_remote() {
	: "${AWS_EC2_HOST_ADDRESS:?}"
	: "${AWS_EC2_USERNAME:?}"
	: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
	: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"

	REMOTE_DIR="$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"

	# Prepare SSH key
	KEY_FILE="$(mktemp)"
	echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
	chmod 400 "$KEY_FILE"

	ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }
	scp_cmd() { scp -i "$KEY_FILE" -o StrictHostKeyChecking=no "$@"; }

	# Ensure working dir
	ssh_cmd "mkdir -p '$REMOTE_DIR'"

	# Ship scripts
	scp_cmd ./docker_run_core.sh        "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/docker_run_core.sh"
	scp_cmd ./docker_remote_run.sh      "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/docker_remote_run.sh"

	# Ship env-file for container
	ENV_TMP="$(mktemp)"
	printenv > "$ENV_TMP"
	scp_cmd "$ENV_TMP" "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/whatsapp_miner.env"
	rm -f "$ENV_TMP"

	# Make scripts executable
	ssh_cmd "chmod +x '$REMOTE_DIR/'*.sh"

	# Execute docker_remote_run.sh with required vars
	ssh_cmd \
		"env -i \
AWS_ECR_LOGIN_PASSWORD='$LOGIN_PW' \
AWS_ECR_REGISTRY='$REGISTRY' \
DOCKER_IMAGE_NAME_WHATSAPP_MINER='$IMAGE_NAME' \
DOCKER_CONTAINER_NAME_WHATSAPP_MINER='$DOCKER_CONTAINER_NAME_WHATSAPP_MINER' \
ENV_FILE='$REMOTE_DIR/whatsapp_miner.env' \
bash '$REMOTE_DIR/docker_remote_run.sh'"

	rm -f "$KEY_FILE"
}

# ── Entrypoint ───────────────────────────────────────────────────────────────
if [[ "$MODE" == "--remote" || "$MODE" == "remote" ]]; then
	run_remote
else
	run_local
fi
