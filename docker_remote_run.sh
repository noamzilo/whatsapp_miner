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

AWS_ECR_LOGIN_PASSWORD="$AWS_ECR_LOGIN_PASSWORD" \
AWS_ECR_REGISTRY="$AWS_ECR_REGISTRY" \
DOCKER_IMAGE_NAME_WHATSAPP_MINER="$DOCKER_IMAGE_NAME_WHATSAPP_MINER" \
DOCKER_CONTAINER_NAME_WHATSAPP_MINER="$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" \
ENV_FILE="$ENV_FILE" \
./docker_run_core.sh
