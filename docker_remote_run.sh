#!/usr/bin/env bash
# Runs ON the EC2 host. Expects env vars from ssh wrapper.

set -euo pipefail

: "${AWS_ECR_LOGIN_PASSWORD:?}"
: "${AWS_ECR_REGISTRY:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${DOCKER_CONTAINER_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"

# Always work in the directory containing this script
cd "$(dirname "$0")"

echo "$AWS_ECR_LOGIN_PASSWORD" | docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" >/dev/null

# Stop & remove any old container
docker rm -f "$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" 2>/dev/null || true

# Pull fresh image & run
docker pull "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
docker run -d --name "$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" --env-file "$ENV_FILE" "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

echo -e "\n🚀✅ Remote container launched successfully ✅🚀\n"
