#!/usr/bin/env bash
# docker_run_core.sh
# Runs (or restarts) containers on *this* host using docker-compose.
# Required env vars (already exported by wrapper):
#   DOCKER_IMAGE_NAME_WHATSAPP_MINER
#   ENV_FILE
#   AWS_ECR_LOGIN_PASSWORD
#   AWS_ECR_REGISTRY
#   DOCKER_COMPOSE_SERVICES           default: all services

set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"
: "${AWS_ECR_LOGIN_PASSWORD:?}"
: "${AWS_ECR_REGISTRY:?}"

COMPOSE_SVCS="${DOCKER_COMPOSE_SERVICES:-}"

# 1│Login to ECR so Compose can pull private image
docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" \
	<<<"$AWS_ECR_LOGIN_PASSWORD"

# 2│Pull and (re)create services
docker compose --env-file "$ENV_FILE" pull $COMPOSE_SVCS || true
docker compose --env-file "$ENV_FILE" up -d $COMPOSE_SVCS

# 3│Health-check each started container
if [[ -z "$COMPOSE_SVCS" ]]; then
	COMPOSE_SVCS="$(docker compose ps --services)"
fi

for SVC in $COMPOSE_SVCS; do
	CID="$(docker compose ps -q "$SVC")"
	[[ -z "$CID" ]] && continue
	sleep 10
	STATUS="$(docker inspect -f '{{.State.Status}}' "$CID")"
	if [[ "$STATUS" != "running" ]]; then
		echo "❌  Service $SVC exited during start-up. Logs:"
		docker logs --tail 200 "$CID" || true
		exit 1
	fi
done

echo -e "\n🚀✅ docker-compose services ($COMPOSE_SVCS) are up ✅🚀\n"
