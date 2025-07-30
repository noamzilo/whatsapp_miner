#!/usr/bin/env bash
# docker_run.sh
#   ./docker_run.sh            → local run (simply defer to docker_run_with_doppler.sh)
#   ./docker_run.sh --remote   → deploy on EC2 via SSH

set -euo pipefail
MODE="${1:-local}"

if [[ "$MODE" == "--remote" || "$MODE" == "remote" ]]; then
	# ── Remote path (unchanged logic) ────────────────────────────────────────
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
	scp_cmd docker_run_core.sh docker-compose.yml docker_remote_run.sh "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/"

	# Temp env on remote
	REMOTE_ENV="/tmp/whatsapp_miner.$RANDOM.env"
	doppler secrets download --no-file --format docker | ssh_cmd "cat > '$REMOTE_ENV'"

	# Execute remote wrapper and clean up temp env
	ssh_cmd "env -i ENV_FILE='$REMOTE_ENV' bash '$REMOTE_DIR/docker_remote_run.sh'; rm -f '$REMOTE_ENV'"

	echo -e "\n🚀✅ Remote stack up via docker-compose ✅🚀\n"
else
	# ── Local path ───────────────────────────────────────────────────────────
	exec ./docker_run_with_doppler.sh
fi
