#!/usr/bin/env bash
# docker_run_core.sh
# Runs (or restarts) containers on *this* host using docker-compose.
# Required env vars (already exported by wrapper):
#   DOCKER_IMAGE_NAME_WHATSAPP_MINER
#   ENV_FILE
#   AWS_ECR_LOGIN_PASSWORD
#   AWS_ECR_REGISTRY
#   DOCKER_COMPOSE_SERVICES           default: all services
#   NEW_IMAGE_DIGEST                  optional: for deployment verification
#   ENVIRONMENT                       dev or prd (default: dev)
#   ENV_NAME                          dev or prd (for container naming)

set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"
: "${AWS_ECR_LOGIN_PASSWORD:?}"
: "${AWS_ECR_REGISTRY:?}"

COMPOSE_SVCS="${DOCKER_COMPOSE_SERVICES:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ENV_NAME="${ENV_NAME:-$ENVIRONMENT}"

# Remove quotes from ENV_NAME if present
ENV_NAME="${ENV_NAME%\"}"
ENV_NAME="${ENV_NAME#\"}"

echo "🔧 Starting docker-compose deployment..."
echo "   Image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "   Environment: $ENVIRONMENT"
echo "   Env Name: $ENV_NAME"
echo "   Services: ${COMPOSE_SVCS:-all}"
echo "   Env file: $ENV_FILE"

# Export ENV_NAME for docker-compose
export ENV_NAME

# 1│Login to ECR so Compose can pull private image
echo "🔐 Logging into ECR..."
docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" <<<"$AWS_ECR_LOGIN_PASSWORD"

# 2│Check if we need to restart containers (only if image changed)
NEED_RESTART=false
if [[ -n "${NEW_IMAGE_DIGEST:-}" ]]; then
    echo "🔍 Checking if containers need restart..."
    
    # Get current running container image digest
    CURRENT_DIGEST=""
    if ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps -q | grep -q .; then
        # Get the image digest of the first running container
        FIRST_CONTAINER="$(ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps -q | head -1)"
        if [[ -n "$FIRST_CONTAINER" ]]; then
            CONTAINER_IMAGE="$(docker inspect --format '{{.Image}}' "$FIRST_CONTAINER" 2>/dev/null || echo "")"
            if [[ -n "$CONTAINER_IMAGE" ]]; then
                # Check if the container is using the same image we're deploying
                if [[ "$CONTAINER_IMAGE" == "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" ]]; then
                    # Use the same method as docker_deploy.sh to get digest
                    CURRENT_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$CONTAINER_IMAGE" | awk '{print $2}' || echo "")"
                else
                    echo "   ⚠️  Container using different image: $CONTAINER_IMAGE (expected: $DOCKER_IMAGE_NAME_WHATSAPP_MINER)"
                fi
            fi
        fi
    fi
    
    echo "   Current digest: ${CURRENT_DIGEST:-none}"
    echo "   New digest:     $NEW_IMAGE_DIGEST"
    
    if [[ -z "$CURRENT_DIGEST" ]]; then
        echo "   🆕 No running containers found - will start new containers"
        NEED_RESTART=true
    elif [[ "$CURRENT_DIGEST" != "$NEW_IMAGE_DIGEST" ]]; then
        echo "   🔄 Image changed - containers will be restarted"
        NEED_RESTART=true
    else
        echo "   ✅ Image unchanged - containers will continue running"
        NEED_RESTART=false
    fi
    
    # Debug: show what containers are currently running
    echo "   📋 Current containers:"
    ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}" || true
else
    echo "   ⚠️  No NEW_IMAGE_DIGEST provided - forcing restart for safety"
    NEED_RESTART=true
fi

# 3│Pull latest images (always do this)
echo "📥 Pulling latest images..."
if [[ -n "$COMPOSE_SVCS" ]]; then
    ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose pull $COMPOSE_SVCS || true
else
    ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose pull || true
fi

# 4│Start/restart services based on need
if [[ "$NEED_RESTART" == "true" ]]; then
    echo "🛑 Stopping existing containers for restart..."
    ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose down --remove-orphans || true
    
    echo "🚀 Starting services with new image..."
    if [[ -n "$COMPOSE_SVCS" ]]; then
        ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose up -d $COMPOSE_SVCS
    else
        ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose up -d
    fi
else
    echo "🚀 Ensuring services are running (no restart needed)..."
    if [[ -n "$COMPOSE_SVCS" ]]; then
        ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose up -d $COMPOSE_SVCS
    else
        ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose up -d
    fi
fi

# 5│Verify something actually started (early catch)
echo "🔍 Checking container status..."
RUNNING_CONTAINERS="$(ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps -q | xargs -r docker inspect --format '{{.State.Status}}' 2>/dev/null | grep -c running || true)"
if [[ "$RUNNING_CONTAINERS" -eq 0 ]]; then
	echo "❌ docker compose up -d did not start any running containers."
	echo "📋 Container status:"
	ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps || true
	echo "📋 Recent logs:"
	ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose logs --tail 50 || true
	exit 1
fi

echo "✅ Found $RUNNING_CONTAINERS running container(s)"

# 6│Health-check each started container
if [[ -z "$COMPOSE_SVCS" ]]; then
	COMPOSE_SVCS="$(ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps --services)"
fi

echo "🏥 Health-checking services: $COMPOSE_SVCS"
for SVC in $COMPOSE_SVCS; do
	CID="$(ENV_FILE="$ENV_FILE" ENV_NAME="$ENV_NAME" docker compose ps -q "$SVC")"
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
