#!/usr/bin/env bash
# docker_run.sh
# Wrapper:
#   ./docker_run.sh            → local compose run
#   ./docker_run.sh --remote   → remote compose run

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
	trap 'rm -f "$ENV_FILE"' EXIT INT TERM

	AWS_ECR_LOGIN_PASSWORD="$LOGIN_PW" \
	AWS_ECR_REGISTRY="$REGISTRY" \
	DOCKER_IMAGE_NAME_WHATSAPP_MINER="$IMAGE_NAME" \
	ENV_FILE="$ENV_FILE" \
	DOCKER_COMPOSE_SERVICES="" \
	./docker_run_core.sh

	echo -e "\n🚀✅ Local stack up via docker-compose (env file removed) ✅🚀\n"
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
	trap 'rm -f "$KEY_FILE"' EXIT INT TERM

	ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }
	scp_cmd() { scp -i "$KEY_FILE" -o StrictHostKeyChecking=no "$@"; }

	# Ensure working dir
	ssh_cmd "mkdir -p '$REMOTE_DIR'"

	# Ship scripts + compose
	scp_cmd ./docker_run_core.sh   "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/docker_run_core.sh"
	scp_cmd ./docker-compose.yml   "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/docker-compose.yml"
	scp_cmd ./docker_remote_run.sh "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/docker_remote_run.sh"

	# Create temp env file remotely
	REMOTE_ENV="/tmp/whatsapp_miner.$RANDOM.env"
	printenv | ssh_cmd "cat > '$REMOTE_ENV'"

	# Execute remote run (compose) and clean env afterwards
	ssh_cmd \
		"set -euo pipefail && \
		env -i \
AWS_ECR_LOGIN_PASSWORD='$LOGIN_PW' \
AWS_ECR_REGISTRY='$REGISTRY' \
DOCKER_IMAGE_NAME_WHATSAPP_MINER='$IMAGE_NAME' \
ENV_FILE='$REMOTE_ENV' \
bash '$REMOTE_DIR/docker_remote_run.sh' && \
rm -f '$REMOTE_ENV'"

	echo -e "\n🚀✅ Remote stack up via docker-compose (env file deleted) ✅🚀\n"
}

# ── Entrypoint ───────────────────────────────────────────────────────────────
if [[ "$MODE" == "--remote" || "$MODE" == "remote" ]]; then
	run_remote
else
	run_local
fi
