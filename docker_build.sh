#!/usr/bin/env bash
# docker_build.sh
# Build the Docker image using env-injected name.
# Usage: ./docker_build.sh [--env dev|prd] [--push]
set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# Parse arguments
PUSH_IMAGE=false
ENVIRONMENT="dev"  # Default to dev

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd] [--push]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'. Must be dev or prd"
    exit 1
fi

echo "🔨 Building Docker image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "🌍 Environment: $ENVIRONMENT"
docker build -t "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" .

if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "📤 Pushing image to registry..."
    docker push "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
    echo "✅ Image pushed successfully"
fi
