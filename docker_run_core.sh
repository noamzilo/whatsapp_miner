#!/usr/bin/env bash
# Runs (or restarts) the container on *any* host.
# Required env-vars (already exported by caller):
#   DOCKER_IMAGE_NAME_WHATSAPP_MINER
#   DOCKER_CONTAINER_NAME_WHATSAPP_MINER
#   ENV_FILE                    – path to .env with runtime secrets
#   AWS_ECR_LOGIN_PASSWORD + AWS_ECR_REGISTRY (for docker login)

set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${DOCKER_CONTAINER_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"
: "${AWS_ECR_LOGIN_PASSWORD:?}"
: "${AWS_ECR_REGISTRY:?}"

# 1 │Login to ECR
docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" \
  <<<"$AWS_ECR_LOGIN_PASSWORD"

# 2 │Pull latest image
docker pull "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

alembic upgrade head

# 3 │Remove *any* existing container with that name (running **or** stopped)
docker ps -aq --filter "name=^/${DOCKER_CONTAINER_NAME_WHATSAPP_MINER}$" \
  | xargs -r docker rm -f

# 4 │Run fresh container (detached)
CID="$(docker run -d \
        --env-file "$ENV_FILE" \
        --name "$DOCKER_CONTAINER_NAME_WHATSAPP_MINER" \
        "$DOCKER_IMAGE_NAME_WHATSAPP_MINER")"

# 5 │Health-check: fail fast if the container exits in the first 10 s
sleep 10
STATUS="$(docker inspect -f '{{.State.Status}}' "$CID")"
if [[ "$STATUS" != "running" ]]; then
  echo "❌  Container exited during start-up. Last 200 log lines:"
  docker logs --tail 200 "$CID" || true
  exit 1
fi

echo -e "\n🚀✅ Container is up and running (ID: $CID) ✅🚀\n"
