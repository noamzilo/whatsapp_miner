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
chmod 400 "$KEY_FILE"
trap 'rm -f "$KEY_FILE"' EXIT INT TERM

ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }

echo ""
echo "🌐 Remote Host: $AWS_EC2_HOST_ADDRESS"
echo "📁 Remote Directory: $REMOTE_DIR"
echo ""

# Check remote container status
echo "🔍 Checking remote container status..."
if ssh_cmd "cd '$REMOTE_DIR' && docker compose ps"; then
    echo ""
    echo "📋 Remote container logs (last 20 lines each):"
    ssh_cmd "cd '$REMOTE_DIR' && docker compose logs --tail 20"
else
    echo "❌ Failed to get remote container status"
fi

echo ""
echo "🏠 Local container status (if any):"
if docker compose ps 2>/dev/null; then
    echo ""
    echo "📋 Local container logs (last 20 lines each):"
    docker compose logs --tail 20 2>/dev/null || true
else
    echo "   No local containers running"
fi 