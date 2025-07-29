#!/usr/bin/env bash
# docker_build.sh
# Build the Docker image using env-injected name.
set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

docker build -t "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" .
