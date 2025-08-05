#!/usr/bin/env bash
# check_deployment.sh
# Simple deployment status check

set -euo pipefail

# Check if we're in Doppler context
if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
    echo "🔄 Re-executing with Doppler context..."
    exec doppler run --preserve-env -- "$0" "$@"
fi

# Map AWS variables from Doppler to standard names
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

# Required variables
: "${AWS_EC2_HOST_ADDRESS:?}"
: "${AWS_EC2_USERNAME:?}"
: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"

echo "🔍 Checking deployment status..."

# Create temp SSH key
KEY_FILE=$(mktemp)
echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
chmod 600 "$KEY_FILE"
trap 'rm -f "$KEY_FILE"' EXIT INT TERM

# Check if containers are running
echo "📋 Checking running containers..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "docker ps --filter 'name=whatsapp_miner' --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"

echo ""
echo "✅ Deployment status check completed!" 