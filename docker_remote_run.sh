#!/usr/bin/env bash
# docker_remote_run.sh
# Runs on EC2; forwards to docker_run_core.sh (compose).

set -euo pipefail
: "${AWS_ECR_LOGIN_PASSWORD:?}"
: "${AWS_ECR_REGISTRY:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"

cd "$(dirname "$0")"

AWS_ECR_LOGIN_PASSWORD="$AWS_ECR_LOGIN_PASSWORD" \
AWS_ECR_REGISTRY="$AWS_ECR_REGISTRY" \
DOCKER_IMAGE_NAME_WHATSAPP_MINER="$DOCKER_IMAGE_NAME_WHATSAPP_MINER" \
ENV_FILE="$ENV_FILE" \
DOCKER_COMPOSE_SERVICES="" \
./docker_run_core.sh
