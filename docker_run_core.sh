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

# Generate environment-specific files for multi-environment processing
echo "📝 Generating environment-specific files..."
ENV_FILE_DEV="$(mktemp)"
ENV_FILE_PRD="$(mktemp)"

# Create environment-specific files
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "🏗️  Running in GitHub Actions - using same env for all environments"
    # In GitHub Actions, use the same env file for all environments
    cp "$ENV_FILE" "$ENV_FILE_DEV"
    cp "$ENV_FILE" "$ENV_FILE_PRD"
else
    echo "🌪️  Running locally - generating environment-specific files"
    # Create dev environment file
    doppler run --project whatsapp_miner_backend --config dev_personal -- bash -c 'doppler secrets download --no-file --format docker' > "$ENV_FILE_DEV"
    
    # Create prd environment file  
    doppler run --project whatsapp_miner_backend --config prd -- bash -c 'doppler secrets download --no-file --format docker' > "$ENV_FILE_PRD"
fi

export ENV_FILE_DEV ENV_FILE_PRD

echo "   Dev env file: $ENV_FILE_DEV"
echo "   Prd env file: $ENV_FILE_PRD"

# 1│Login to ECR so Compose can pull private image
echo "🔐 Logging into ECR..."
docker login --username AWS --password-stdin "$AWS_ECR_REGISTRY" <<<"$AWS_ECR_LOGIN_PASSWORD"

# 2│Check if we need to restart containers (only if image changed)
NEED_RESTART=false
if [[ -n "${NEW_IMAGE_DIGEST:-}" ]]; then
    echo "🔍 Checking if containers need restart..."
    
    # Get current running container image digest
    CURRENT_DIGEST=""
    if ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps -q | grep -q .; then
        # Get the image digest of the first running container
        FIRST_CONTAINER="$(ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps -q | head -1)"
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
    ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps --format "table {{.Name}}\t{{.Image}}\t{{.Status}}" || true
else
    echo "   ⚠️  No NEW_IMAGE_DIGEST provided - forcing restart for safety"
    NEED_RESTART=true
fi

# 3│Pull latest images (always do this)
echo "📥 Pulling latest images..."
if [[ -n "$COMPOSE_SVCS" ]]; then
    ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose pull $COMPOSE_SVCS || true
else
    ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose pull || true
fi

# 4│Start/restart services based on need
if [[ "$NEED_RESTART" == "true" ]]; then
    echo "🛑 Stopping existing containers for restart..."
    ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose down --remove-orphans || true
    
    echo "🚀 Starting services with new image..."
    if [[ -n "$COMPOSE_SVCS" ]]; then
        ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose up -d $COMPOSE_SVCS
    else
        ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose up -d
    fi
else
    echo "🚀 Ensuring services are running (no restart needed)..."
    if [[ -n "$COMPOSE_SVCS" ]]; then
        ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose up -d $COMPOSE_SVCS
    else
        ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose up -d
    fi
fi

# 5│Verify something actually started (early catch)
echo "🔍 Checking container status..."
RUNNING_CONTAINERS="$(ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps -q | xargs -r docker inspect --format '{{.State.Status}}' 2>/dev/null | grep -c running || true)"
if [[ "$RUNNING_CONTAINERS" -eq 0 ]]; then
	echo "❌ docker compose up -d did not start any running containers."
	echo "📋 Container status:"
	ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps || true
	echo "📋 Recent logs:"
	ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose logs --tail 50 || true
	exit 1
fi

echo "✅ Found $RUNNING_CONTAINERS running container(s)"

# 6│Health-check each started container
if [[ -z "$COMPOSE_SVCS" ]]; then
	COMPOSE_SVCS="$(ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps --services)"
fi

echo "🏥 Health-checking services: $COMPOSE_SVCS"
for SVC in $COMPOSE_SVCS; do
	CID="$(ENV_FILE="$ENV_FILE" ENV_FILE_DEV="$ENV_FILE_DEV" ENV_FILE_PRD="$ENV_FILE_PRD" docker compose ps -q "$SVC")"
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
