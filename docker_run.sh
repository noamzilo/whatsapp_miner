#!/usr/bin/env bash
# docker_run.sh
#   ./docker_run.sh [--env dev|prd]            → local run (simply defer to docker_run_with_doppler.sh)
#   ./docker_run.sh [--env dev|prd] --remote   → deploy on EC2 via SSH

set -euo pipefail

# Parse arguments
ENVIRONMENT="development"  # Default to development
MODE="local"

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --remote)
            MODE="remote"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd] [--remote]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'. Must be dev or prd"
    exit 1
fi

echo "🌍 Environment: $ENVIRONMENT"
echo "🚀 Mode: $MODE"

if [[ "$MODE" == "remote" ]]; then
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
	chmod 600 "$KEY_FILE"
	trap 'rm -f "$KEY_FILE"' EXIT INT TERM

	# Create log file for SSH/SCP commands
	LOG_FILE="ssh_log.log"
	rm -f "$LOG_FILE"

	# Function to log SSH commands
	log_ssh_cmd() {
		echo "=== SSH Command: $* ===" >> "$LOG_FILE"
		ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@" 2>&1 | tee -a "$LOG_FILE"
		return ${PIPESTATUS[0]}
	}

	# Function to log SCP commands
	log_scp_cmd() {
		echo "=== SCP Command: $* ===" >> "$LOG_FILE"
		scp -i "$KEY_FILE" -o StrictHostKeyChecking=no "$@" 2>&1 | tee -a "$LOG_FILE"
		return ${PIPESTATUS[0]}
	}

	ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }
	scp_cmd() { scp -i "$KEY_FILE" -o StrictHostKeyChecking=no "$@"; }

	# Ensure working dir
	echo "🔧 Creating remote directory: $REMOTE_DIR"
	log_ssh_cmd "mkdir -p '$REMOTE_DIR' && echo 'Directory created successfully'"

	# Ship scripts + compose
	echo "📦 Copying files to remote..."
	log_scp_cmd docker_run_core.sh docker-compose.yml docker_remote_run.sh "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:$REMOTE_DIR/"
	log_ssh_cmd "ls -la '$REMOTE_DIR'"

	# Create temp env on remote - pass ALL environment variables automatically
	REMOTE_ENV="/tmp/whatsapp_miner.$RANDOM.env"
	
	if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
		# GitHub Actions: export ALL environment variables to remote .env file
		env | sed 's/^/export /' | ssh_cmd "cat > '$REMOTE_ENV'"
	else
		# Local: use Doppler to create .env with all variables
		doppler secrets download --no-file --format docker | ssh_cmd "cat > '$REMOTE_ENV'"
	fi

	# Execute remote wrapper and clean up temp env
	# Pass DIGEST_FILE_PATH for deployment verification
	# Change to remote directory before executing
	if log_ssh_cmd "cd '$REMOTE_DIR' && ENV_FILE='$REMOTE_ENV' DIGEST_FILE_PATH='${DIGEST_FILE_PATH:-}' ENVIRONMENT='$ENVIRONMENT' bash docker_remote_run.sh; rm -f '$REMOTE_ENV'"; then
		echo -e "\n🚀✅ Remote stack up via docker-compose ✅🚀\n"
	else
		echo -e "\n❌ Remote deployment failed!\n"
		echo "📋 SSH log saved to: $LOG_FILE"
		exit 1
	fi
else
	# ── Local path ───────────────────────────────────────────────────────────
	export ENVIRONMENT="$ENVIRONMENT"
	exec ./docker_run_with_doppler.sh
fi

