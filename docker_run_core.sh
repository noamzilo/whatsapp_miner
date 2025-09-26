#!/usr/bin/env bash
# docker_run_core.sh
# Runs (or restarts) containers on *this* host using docker-compose.
# Required env vars (already exported by wrapper):
#   DOCKER_IMAGE_NAME_WHATSAPP_MINER
#   DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER
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
: "${DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER:?}"
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

# Compute environment-specific image names if not provided explicitly
make_env_specific() {
    local image_name="$1"
    local env_tag="$2"
    local clean="${image_name%\"}"; clean="${clean#\"}"
    # If tag exists, keep it; else append env tag
    if [[ "$clean" == *:* ]]; then
        printf "%s" "$clean"
    else
        printf "%s:%s" "$clean" "$env_tag"
    fi
}

# Use provided env-specific names or derive from base + ENV_NAME
MINER_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV:-$(make_env_specific "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" "$ENV_NAME")}"
CLASSIFIER_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER_ENV:-$(make_env_specific "$DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER" "$ENV_NAME")}"

echo "🔧 Starting docker-compose deployment..."
echo "   Miner base image:       $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "   Miner env image:        $MINER_IMAGE_NAME"
echo "   Classifier base image:  $DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER"
echo "   Classifier env image:   $CLASSIFIER_IMAGE_NAME"
echo "   Environment: $ENVIRONMENT"
echo "   Env Name: $ENV_NAME"
echo "   Services: ${COMPOSE_SVCS:-all}"
echo "   Env file: $ENV_FILE"

# Export the image names for docker-compose (this is what docker-compose.yml expects)
export DOCKER_IMAGE_NAME_WHATSAPP_MINER="$MINER_IMAGE_NAME"
export DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER="$CLASSIFIER_IMAGE_NAME"
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

# Get ECR registries from cleaned image names (deduplicated, host only)
REGISTRIES=()
add_registry() {
    local name="$1"
    local clean="${name%\"}"; clean="${clean#\"}"
    local host="${clean%%/*}"
    if [[ -n "$host" ]]; then
        for r in "${REGISTRIES[@]:-}"; do [[ "$r" == "$host" ]] && return; done
        REGISTRIES+=("$host")
    fi
}
add_registry "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
add_registry "$DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER"

echo "🔍 Debug: ECR_REGISTRIES: ${REGISTRIES[*]:-none}"

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

for ECR_REGISTRY in "${REGISTRIES[@]:-}"; do
    # Use AWS CLI with the credential files
    ECR_PASSWORD=$(aws ecr get-login-password --region "$AWS_DEFAULT_REGION")

    # Configure Docker to use a writable location for credentials
    DOCKER_CONFIG_DIR="/tmp/docker_config_$$"
    mkdir -p "$DOCKER_CONFIG_DIR"
    chmod 700 "$DOCKER_CONFIG_DIR"
    export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"

    # Login to the specific registry
    echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

    # Clean up Docker config per registry
    rm -rf "$DOCKER_CONFIG_DIR"
done

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
    
    # If a digest file is provided (combined for miner/classifier), force restart to apply new images
    NEED_RESTART=true
    if [[ -n "${DIGEST_FILE_PATH:-}" && -f "$DIGEST_FILE_PATH" ]]; then
        echo "   🔍 Digest file present - forcing restart to apply new images"
    else
        echo "   ⚠️  No NEW_IMAGE_DIGEST provided - forcing restart for safety"
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
