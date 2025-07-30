#!/usr/bin/env bash
# docker_deploy.sh
# Build, push and restart the container on the remote host.
set -euo pipefail

: "${AWS_EC2_REGION:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# Map IAM → AWS CLI
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

# Validate deployment setup before starting
echo "🔍 Validating deployment setup..."
./docker_validate_setup.sh

# Login to ECR
aws ecr get-login-password --region "$AWS_EC2_REGION" \
	| docker login --username AWS --password-stdin "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

./docker_build.sh
docker push "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

# Get the image digest for verification
NEW_IMAGE_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" | awk '{print $2}')"
echo "📦 New image digest: $NEW_IMAGE_DIGEST"

# Export for verification in remote script
export NEW_IMAGE_DIGEST

# Restart container on EC2
./docker_run.sh --remote

# Show final status
echo "📊 Final deployment status:"
./docker_show_status.sh

echo ""
echo "🚀✅ DONE: WhatsApp Miner deployment completed successfully ✅🚀"
echo "   New image digest: $NEW_IMAGE_DIGEST"
echo ""