#!/usr/bin/env bash
# docker_run.sh
#   ./docker_run.sh            → local run (simply defer to docker_run_with_doppler.sh)
#   ./docker_run.sh --remote   → deploy on EC2 via SSH

set -euo pipefail
MODE="${1:-local}"

if [[ "$MODE" == "--remote" || "$MODE" == "remote" ]]; then
	# ── Remote path ───────────────────────────────────────────────────────────
	# Check if we're in GitHub Actions or local environment
	if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
		echo "🏗️  Running in GitHub Actions environment"
		# GitHub Actions: use environment variables directly
		: "${AWS_EC2_HOST_ADDRESS:?}"
		: "${AWS_EC2_USERNAME:?}"
		: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
		: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"
		
		# AWS variables are already set from GitHub secrets
		: "${AWS_ACCESS_KEY_ID:?}"
		: "${AWS_SECRET_ACCESS_KEY:?}"
		: "${AWS_DEFAULT_REGION:?}"
	else
		# Local: check if we're in Doppler context, if not, re-exec with Doppler
		if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
			echo "🔄 Re-executing with Doppler context..."
			exec doppler run --preserve-env -- "$0" "$@"
		fi

		# ── Map AWS variables from Doppler to standard names ─────────────────────
		export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
		export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
		export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

		# ── Required variables (now mapped from Doppler) ─────────────────────────
		: "${AWS_EC2_HOST_ADDRESS:?}"
		: "${AWS_EC2_USERNAME:?}"
		: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
		: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"
	fi

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

	# Create temp env on remote - pass ALL environment variables automatically
	REMOTE_ENV="/tmp/whatsapp_miner.$RANDOM.env"
	
	if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
		# GitHub Actions: export ALL environment variables to remote .env file
		# No filtering - pass EVERYTHING
		env | ssh_cmd "cat > '$REMOTE_ENV'"
	else
		# Local: use Doppler to create .env with all variables
		doppler secrets download --no-file --format docker | ssh_cmd "cat > '$REMOTE_ENV'"
	fi

	# Execute remote wrapper and clean up temp env
	# Pass NEW_IMAGE_DIGEST for deployment verification
	# Change to remote directory before executing
	ssh_cmd "cd '$REMOTE_DIR' && env -i ENV_FILE='$REMOTE_ENV' NEW_IMAGE_DIGEST='${NEW_IMAGE_DIGEST:-}' bash docker_remote_run.sh; rm -f '$REMOTE_ENV'"

	echo -e "\n🚀✅ Remote stack up via docker-compose ✅🚀\n"
else
	# ── Local path ───────────────────────────────────────────────────────────
	exec ./docker_run_with_doppler.sh
fi
