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

echo "🔧 Starting docker-compose deployment..."
echo "   Image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "   Services: ${COMPOSE_SVCS:-all}"
echo "   Env file: $ENV_FILE"

# 1│Login to ECR so Compose can pull private image
echo "🔐 Logging into ECR..."
docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" <<<"$AWS_ECR_LOGIN_PASSWORD"

# 2│Stop existing containers to ensure clean deployment
echo "🛑 Stopping existing containers..."
docker compose --env-file "$ENV_FILE" down --remove-orphans || true

# 3│Pull and (re)create services
echo "📥 Pulling latest images..."
docker compose --env-file "$ENV_FILE" pull $COMPOSE_SVCS || true

echo "🚀 Starting services..."
docker compose --env-file "$ENV_FILE" up -d $COMPOSE_SVCS

# 4│Verify something actually started (early catch)
echo "🔍 Checking container status..."
RUNNING_CONTAINERS="$(docker compose ps -q | xargs -r docker inspect --format '{{.State.Status}}' 2>/dev/null | grep -c running || true)"
if [[ "$RUNNING_CONTAINERS" -eq 0 ]]; then
	echo "❌ docker compose up -d did not start any running containers."
	echo "📋 Container status:"
	docker compose ps || true
	echo "📋 Recent logs:"
	docker compose logs --tail 50 || true
	exit 1
fi

echo "✅ Found $RUNNING_CONTAINERS running container(s)"

# 5│Health-check each started container
if [[ -z "$COMPOSE_SVCS" ]]; then
	COMPOSE_SVCS="$(docker compose ps --services)"
fi

echo "🏥 Health-checking services: $COMPOSE_SVCS"
for SVC in $COMPOSE_SVCS; do
	CID="$(docker compose ps -q "$SVC")"
	[[ -z "$CID" ]] && continue
	
	echo "   Checking $SVC (container: $CID)..."
	sleep 10
	STATUS="$(docker inspect -f '{{.State.Status}}' "$CID")"
	if [[ "$STATUS" != "running" ]]; then
		echo "❌  Service $SVC exited during start-up. Logs:"
		docker logs --tail 200 "$CID" || true
		exit 1
	fi
	echo "   ✅ $SVC is running"
done

echo -e "\n🚀✅ docker-compose services ($COMPOSE_SVCS) are up ✅🚀\n"
