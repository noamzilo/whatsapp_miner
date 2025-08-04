#!/usr/bin/env bash
# docker_deploy.sh
# Build, push, run migrations, and restart the container on the remote host.
# Usage: ./docker_deploy.sh [--env dev|prd]
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

echo "🌍 Environment: $ENVIRONMENT"

: "${AWS_EC2_REGION:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# Map IAM → AWS CLI (works for both Doppler and GitHub Actions)
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

# Map region variable (works for both Doppler and GitHub Actions)
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_EC2_REGION}"

# Validate deployment setup before starting
echo "🔍 Validating deployment setup..."
./docker_validate_setup.sh --env "$ENVIRONMENT"

# Get ECR registry from cleaned image name
ECR_REGISTRY="${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

# Login to ECR
aws ecr get-login-password --region "$AWS_EC2_REGION" \
	| docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Build and push image
echo "🔨 Building and pushing image..."
./docker_build.sh --env "$ENVIRONMENT" --push

# Get the image digest for verification
NEW_IMAGE_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" | awk '{print $2}')"
echo "📦 New image digest: $NEW_IMAGE_DIGEST"

# Export for verification in remote script
export NEW_IMAGE_DIGEST

# Run migrations for the specified environment
echo "🗄️  Running database migrations for environment: $ENVIRONMENT"
./run_migrations.sh --env "$ENVIRONMENT"

# Deploy to remote
echo "🚀 Deploying to remote host..."
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "🏗️  Running in GitHub Actions - using GitHub secrets"
    ./docker_run.sh --env "$ENVIRONMENT" --remote
else
    echo "🌪️  Running locally - using Doppler secrets"
    ./docker_run.sh --env "$ENVIRONMENT" --remote
fi

# Show final status
echo "📊 Final deployment status:"
./docker_show_status.sh --env "$ENVIRONMENT"

echo ""
echo "🚀✅ DONE: WhatsApp Miner deployment completed successfully ✅🚀"
echo "   Environment: $ENVIRONMENT"
echo "   New image digest: $NEW_IMAGE_DIGEST"
echo ""