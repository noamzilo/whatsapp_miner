#!/usr/bin/env bash
# docker_deploy.sh
# Build, push, run migrations, and restart the container on the remote host.
set -euo pipefail

: "${AWS_EC2_REGION:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# Map IAM → AWS CLI (works for both Doppler and GitHub Actions)
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

# Validate deployment setup before starting
echo "🔍 Validating deployment setup..."
./docker_validate_setup.sh

# Login to ECR
aws ecr get-login-password --region "$AWS_EC2_REGION" \
	| docker login --username AWS --password-stdin "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

# Build and push image
echo "🔨 Building and pushing image..."
./docker_build.sh --push

# Get the image digest for verification
NEW_IMAGE_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" | awk '{print $2}')"
echo "📦 New image digest: $NEW_IMAGE_DIGEST"

# Export for verification in remote script
export NEW_IMAGE_DIGEST

# Run migrations before deployment
echo "🗄️  Running database migrations..."
./run_migrations.sh --env dev
./run_migrations.sh --env prd

# Deploy to remote
echo "🚀 Deploying to remote host..."
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "🏗️  Running in GitHub Actions - using GitHub secrets"
    ./docker_run.sh --remote
else
    echo "🌪️  Running locally - using Doppler secrets"
    ./docker_run.sh --remote
fi

# Show final status
echo "📊 Final deployment status:"
./docker_show_status.sh

echo ""
echo "🚀✅ DONE: WhatsApp Miner deployment completed successfully ✅🚀"
echo "   New image digest: $NEW_IMAGE_DIGEST"
echo ""