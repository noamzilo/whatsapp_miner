#!/usr/bin/env bash
# docker_show_status.sh
# Shows container status for local and remote deployments
# Usage: ./docker_show_status.sh [--env dev|prd]

set -euo pipefail

# Parse arguments
ENVIRONMENT="dev"  # Default to dev

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'. Must be dev or prd"
    exit 1
fi

echo "📊 Container Status for Environment: $ENVIRONMENT"
echo "=================================================="

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

ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }

echo ""
echo "🌐 Remote Host: $AWS_EC2_HOST_ADDRESS"
echo "📁 Remote Directory: $REMOTE_DIR"
echo ""

# Check remote container status
echo "🔍 Checking remote container status..."
# Create temp env file on remote with all variables
REMOTE_ENV="/tmp/whatsapp_miner_status.$RANDOM.env"
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    # Export all environment variables in proper format
    env | sed 's/^/export /' | ssh_cmd "cat > '$REMOTE_ENV'"
else
    doppler secrets download --no-file --format docker | ssh_cmd "cat > '$REMOTE_ENV'"
fi

# Create log file for SSH commands
LOG_FILE="ssh_log.log"
rm -f "$LOG_FILE"

# Function to log SSH commands
log_ssh_cmd() {
    echo "=== SSH Command: $* ===" >> "$LOG_FILE"
    ssh_cmd "$@" 2>&1 | tee -a "$LOG_FILE"
    return ${PIPESTATUS[0]}
}

# Debug: List what's actually in the remote directory
echo "   🔍 Checking remote directory contents..."
log_ssh_cmd "ls -la '$REMOTE_DIR'"

# Check if any containers are running (regardless of docker-compose)
echo "   🔍 Checking for running containers..."
log_ssh_cmd "docker ps --filter 'name=whatsapp_miner' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"

# Try docker-compose status if files exist
if log_ssh_cmd "test -f '$REMOTE_DIR/docker-compose.yml'"; then
    echo "   🔍 Checking docker-compose status..."
    log_ssh_cmd "mkdir -p '$REMOTE_DIR' && cd '$REMOTE_DIR' && set -a && source '$REMOTE_ENV' && set +a && ENV_FILE='$REMOTE_ENV' ENV_NAME='$ENVIRONMENT' docker compose ps"
    echo ""
    echo "📋 Remote container logs (last 20 lines each):"
    log_ssh_cmd "cd '$REMOTE_DIR' && set -a && source '$REMOTE_ENV' && set +a && ENV_FILE='$REMOTE_ENV' ENV_NAME='$ENVIRONMENT' docker compose logs --tail 20"
else
    echo "   ⚠️  docker-compose.yml not found on remote, but containers might still be running"
fi

log_ssh_cmd "rm -f '$REMOTE_ENV'"

echo ""
echo "🏠 Local container status (if any):"
if docker compose ps 2>/dev/null; then
    echo ""
    echo "📋 Local container logs (last 20 lines each):"
    docker compose logs --tail 20 2>/dev/null || true
else
    echo "   No local containers running"
fi 