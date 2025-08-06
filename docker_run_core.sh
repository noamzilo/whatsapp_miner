#!/usr/bin/env bash
# docker_run_core.sh
# Runs (or restarts) containers on *this* host using docker-compose.
# Required env vars (already exported by wrapper):
#   DOCKER_IMAGE_NAME_WHATSAPP_MINER
#   ENV_FILE
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   AWS_DEFAULT_REGION
#   DOCKER_COMPOSE_SERVICES           default: all services
#   NEW_IMAGE_DIGEST                  optional: for deployment verification
#   ENVIRONMENT                       dev or prd (default: dev)
#   ENV_NAME                          dev or prd (for container naming)

set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"
: "${ENV_FILE:?}"
: "${AWS_ACCESS_KEY_ID:?}"
: "${AWS_SECRET_ACCESS_KEY:?}"
: "${AWS_DEFAULT_REGION:?}"

COMPOSE_SVCS="${DOCKER_COMPOSE_SERVICES:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ENV_NAME="${ENV_NAME:-$ENVIRONMENT}"

# Remove quotes from ENV_NAME if present
ENV_NAME="${ENV_NAME%\"}"
ENV_NAME="${ENV_NAME#\"}"

# Use environment-specific image name if available, otherwise fall back to base
IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV:-$DOCKER_IMAGE_NAME_WHATSAPP_MINER}"

echo "🔧 Starting docker-compose deployment..."
echo "   Base image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "   Environment-specific image: $IMAGE_NAME"
echo "   Environment: $ENVIRONMENT"
echo "   Env Name: $ENV_NAME"
echo "   Services: ${COMPOSE_SVCS:-all}"
echo "   Env file: $ENV_FILE"

# Export the image name for docker-compose (this is what docker-compose.yml expects)
export DOCKER_IMAGE_NAME_WHATSAPP_MINER="$IMAGE_NAME"
export ENV_NAME

# Source environment file to make variables available to docker-compose
if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
    echo "📋 Loading environment variables from: $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️  Warning: ENV_FILE not found or empty: $ENV_FILE"
fi

# 1│Login to ECR so Compose can pull private image
echo "🔐 Logging into ECR..."
echo "🔍 Debug: Current user: $(whoami)"
echo "🔍 Debug: AWS_ACCESS_KEY_ID length: ${#AWS_ACCESS_KEY_ID}"
echo "🔍 Debug: AWS_SECRET_ACCESS_KEY length: ${#AWS_SECRET_ACCESS_KEY}"
echo "🔍 Debug: AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION"

# Get ECR registry from cleaned image name
CLEAN_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
CLEAN_IMAGE_NAME="${CLEAN_IMAGE_NAME#\"}"
ECR_REGISTRY="${CLEAN_IMAGE_NAME%/*}"

echo "🔍 Debug: ECR_REGISTRY: $ECR_REGISTRY"

# Create AWS credential files in a writable location
AWS_CREDS_DIR="/tmp/aws_creds_$$"
mkdir -p "$AWS_CREDS_DIR"
chmod 700 "$AWS_CREDS_DIR"

export AWS_SHARED_CREDENTIALS_FILE="$AWS_CREDS_DIR/credentials"
export AWS_CONFIG_FILE="$AWS_CREDS_DIR/config"

# Create the credential files with proper content
cat > "$AWS_SHARED_CREDENTIALS_FILE" << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF

cat > "$AWS_CONFIG_FILE" << EOF
[default]
region = $AWS_DEFAULT_REGION
output = json
EOF

chmod 600 "$AWS_SHARED_CREDENTIALS_FILE" "$AWS_CONFIG_FILE"

# Use AWS CLI with the credential files
ECR_PASSWORD=$(aws ecr get-login-password --region "$AWS_DEFAULT_REGION")

# Configure Docker to use a writable location for credentials
DOCKER_CONFIG_DIR="/tmp/docker_config_$$"
mkdir -p "$DOCKER_CONFIG_DIR"
chmod 700 "$DOCKER_CONFIG_DIR"
export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"

# Use AWS CLI with the credential files
echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Clean up Docker config
rm -rf "$DOCKER_CONFIG_DIR"

# Clean up credential files
rm -rf "$AWS_CREDS_DIR"

# 2│Check for any existing containers using our image (regardless of how they were started)
echo "🔍 Checking for existing containers using our image..."
EXISTING_CONTAINERS="$(docker ps --filter "ancestor=$DOCKER_IMAGE_NAME_WHATSAPP_MINER" --format "{{.Names}}" 2>/dev/null || echo "")"

if [[ -n "$EXISTING_CONTAINERS" ]]; then
    echo "   📋 Found existing containers using our image:"
    echo "$EXISTING_CONTAINERS" | while read -r container; do
        echo "      - $container"
    done
    
    # Check if any of these containers are using the new image digest
    NEED_RESTART=true
    NEW_IMAGE_DIGEST=""
    if [[ -n "${DIGEST_FILE_PATH:-}" && -f "$DIGEST_FILE_PATH" ]]; then
        NEW_IMAGE_DIGEST="$(cat "$DIGEST_FILE_PATH")"
    fi
    
    if [[ -n "${NEW_IMAGE_DIGEST:-}" ]]; then
        echo "   🔍 Checking if existing containers need restart..."
        
        # Get current image digest from any running container
        CURRENT_DIGEST=""
        for container in $EXISTING_CONTAINERS; do
            CONTAINER_IMAGE="$(docker inspect --format '{{.Image}}' "$container" 2>/dev/null || echo "")"
            if [[ -n "$CONTAINER_IMAGE" ]]; then
                # Use the same method as docker_deploy.sh to get digest
                CURRENT_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$CONTAINER_IMAGE" | awk '{print $2}' || echo "")"
                if [[ -n "$CURRENT_DIGEST" ]]; then
                    break  # Found a digest, no need to check more containers
                fi
            fi
        done
        
        echo "   Current digest: ${CURRENT_DIGEST:-none}"
        echo "   New digest:     $NEW_IMAGE_DIGEST"
        
        if [[ -z "$CURRENT_DIGEST" ]]; then
            echo "   🆕 Could not determine current digest - will restart containers"
            NEED_RESTART=true
        elif [[ "$CURRENT_DIGEST" != "$NEW_IMAGE_DIGEST" ]]; then
            echo "   🔄 Image changed - containers will be restarted"
            NEED_RESTART=true
        else
            echo "   ✅ Image unchanged - containers will continue running"
            NEED_RESTART=false
        fi
    else
        echo "   ⚠️  No NEW_IMAGE_DIGEST provided - forcing restart for safety"
        NEED_RESTART=true
    fi
else
    echo "   🆕 No existing containers found using our image"
    NEED_RESTART=true
fi

# 3│Pull latest images (always do this)
echo "📥 Pulling latest images..."
if [[ -n "$COMPOSE_SVCS" ]]; then
    docker compose pull $COMPOSE_SVCS || true
else
    docker compose pull || true
fi

# 4│Start/restart services based on need
if [[ "$NEED_RESTART" == "true" ]]; then
    echo "🛑 Stopping existing containers for restart..."
    
    # Stop any existing containers using our image (regardless of how they were started)
    if [[ -n "$EXISTING_CONTAINERS" ]]; then
        echo "   Stopping existing containers..."
        echo "$EXISTING_CONTAINERS" | xargs -r docker stop || true
        echo "$EXISTING_CONTAINERS" | xargs -r docker rm || true
    fi
    
    # Also stop any docker-compose managed containers and remove them
    docker compose down --remove-orphans --volumes || true
    
    # Force remove any containers with our naming pattern to avoid conflicts
    # Note: This docker ps command is necessary to find containers started outside docker-compose
    echo "   Removing any conflicting containers..."
    docker ps -a --filter "name=whatsapp_miner" --format "{{.ID}}" | xargs -r docker rm -f || true
    
    echo "🚀 Starting services with new image..."
    if [[ -n "$COMPOSE_SVCS" ]]; then
        echo "   Starting specific services: $COMPOSE_SVCS"
        docker compose up -d $COMPOSE_SVCS
    else
        echo "   Starting all services"
        docker compose up -d
    fi

    # Show service status immediately after starting
    echo "📋 Service status after start:"
    docker compose ps || true
else
    echo "🚀 Ensuring services are running (no restart needed)..."
    if [[ -n "$COMPOSE_SVCS" ]]; then
        docker compose up -d $COMPOSE_SVCS
    else
        docker compose up -d
    fi
fi

# 5│Verify something actually started (early catch)
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

# 6│Health-check each started container
if [[ -z "$COMPOSE_SVCS" ]]; then
	COMPOSE_SVCS="$(docker compose ps --services)"
fi

echo "🏥 Health-checking services: $COMPOSE_SVCS"
for SVC in $COMPOSE_SVCS; do
	CID="$(docker compose ps -q "$SVC")"
	[[ -z "$CID" ]] && continue
	
	echo "   Checking $SVC (container: $CID)..."
	STATUS="$(docker inspect -f '{{.State.Status}}' "$CID")"
	if [[ "$STATUS" != "running" ]]; then
		echo "❌  Service $SVC exited during start-up. Logs:"
		docker compose logs --tail 200 "$SVC" || true
		exit 1
	fi
	echo "   ✅ $SVC is running"
done

echo -e "\n🚀✅ docker-compose services ($COMPOSE_SVCS) are up ✅🚀\n"
