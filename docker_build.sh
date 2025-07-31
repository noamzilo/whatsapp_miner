#!/usr/bin/env bash
# docker_build.sh
# Build the Docker image using env-injected name.
# Usage: ./docker_build.sh [--push]
set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# Parse arguments
PUSH_IMAGE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--push]"
            exit 1
            ;;
    esac
done

echo "🔨 Building Docker image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
docker build -t "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" .

if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "📤 Pushing image to registry..."
    docker push "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
    echo "✅ Image pushed successfully"
fi
