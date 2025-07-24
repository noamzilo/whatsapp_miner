#!/usr/bin/env bash
# Runs (or restarts) the container on *any* host.
# Expects these env-vars to be pre-exported by the caller:
#   DOCKER_IMAGE_NAME_WHATSAPP_MINER
#   DOCKER_CONTAINER_NAME_WHATSAPP_MINER
#   ENV_FILE                       – path to .env with runtime secrets
#   AWS_ECR_LOGIN_PASSWORD + AWS_ECR_REGISTRY (for docker login)

set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${DOCKER_CONTAINER_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"
: "${AWS_ECR_LOGIN_PASSWORD:?}"
: "${AWS_ECR_REGISTRY:?}"

# 1│Login to the registry
docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" <<<"$AWS_ECR_LOGIN_PASSWORD"

# 2│Ensure we have the latest image
docker pull "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

# 3│Stop/remove any running instance of this image
docker ps -q --filter "name=${DOCKER_CONTAINER_NAME_WHATSAPP_MINER}" | xargs -r docker rm -f

# 4│Run the container (detached)
docker run -d \
	--env-file "$ENV_FILE" \
	--name "$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" \
	"$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
