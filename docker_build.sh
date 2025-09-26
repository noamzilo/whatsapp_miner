#!/usr/bin/env bash
# docker_build.sh
# Build WhatsApp Miner images using docker-compose (miner + classifier).
# Usage:
#   ./docker_build.sh [--env dev|prd] [--push]
#                     [--miner-image IMAGE] [--classifier-image IMAGE]
#                     [--region REGION] [--access-key KEY] [--secret-key KEY]
set -euo pipefail

# Parse arguments
PUSH_IMAGE=false
ENV_NAME="dev"  # Default to dev
DOCKER_IMAGE_NAME_WHATSAPP_MINER="${DOCKER_IMAGE_NAME_WHATSAPP_MINER:-}"
DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER="${DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER:-}"
AWS_DEFAULT_REGION=""
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        --image-name)
            # Backward compatibility: sets miner image
            DOCKER_IMAGE_NAME_WHATSAPP_MINER="$2"
            shift 2
            ;;
        --miner-image)
            DOCKER_IMAGE_NAME_WHATSAPP_MINER="$2"
            shift 2
            ;;
        --classifier-image)
            DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER="$2"
            shift 2
            ;;
        --region)
            AWS_DEFAULT_REGION="$2"
            shift 2
            ;;
        --access-key)
            AWS_ACCESS_KEY_ID="$2"
            shift 2
            ;;
        --secret-key)
            AWS_SECRET_ACCESS_KEY="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd] [--push] [--image-name IMAGE_NAME] [--region REGION] [--access-key ACCESS_KEY] [--secret-key SECRET_KEY]"
            exit 1
            ;;
    esac
done

# Validate required image names (allow env fallbacks)
if [[ -z "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" ]]; then
    echo "❌ Error: miner image is required. Provide --miner-image or DOCKER_IMAGE_NAME_WHATSAPP_MINER env"
    exit 1
fi
if [[ -z "$DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER" ]]; then
    echo "❌ Error: classifier image is required. Provide --classifier-image or DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER env"
    exit 1
fi

# Validate environment
if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENV_NAME'. Must be dev or prd"
    exit 1
fi

# If pushing, ensure we have required variables and authenticate with ECR
if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "🔐 Setting up ECR authentication for push..."
    
    # Validate required variables for push
    if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
        echo "❌ Error: --access-key is required when --push is specified"
        exit 1
    fi
    
    if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
        echo "❌ Error: --secret-key is required when --push is specified"
        exit 1
    fi
    
    if [[ -z "$AWS_DEFAULT_REGION" ]]; then
        echo "❌ Error: --region is required when --push is specified"
        exit 1
    fi
    
    # Export AWS credentials
    export AWS_ACCESS_KEY_ID
    export AWS_SECRET_ACCESS_KEY
    export AWS_DEFAULT_REGION
    
    # Get ECR registry host from cleaned miner image name (assume same registry for both)
    CLEAN_MINER_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
    CLEAN_MINER_IMAGE_NAME="${CLEAN_MINER_IMAGE_NAME#\"}"
    ECR_REGISTRY_HOST="${CLEAN_MINER_IMAGE_NAME%%/*}"
    
    # Login to ECR
    echo "🔐 Logging into ECR registry: $ECR_REGISTRY_HOST"
    
    # Use AWS CLI to get ECR password (simpler approach that was working)
    ECR_PASSWORD=$(aws ecr get-login-password --region "$AWS_DEFAULT_REGION")
    
    # Login to Docker with ECR password
    echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin "$ECR_REGISTRY_HOST"

    # Ensure ECR repositories exist for miner and classifier
    ensure_repo() {
        local image="$1"
        local clean="${image%\"}"; clean="${clean#\"}"
        # Remove tag if present
        local no_tag="${clean%:*}"
        # Extract repository path after registry host
        local repo_path="${no_tag#*/}"
        echo "🔎 Ensuring ECR repository exists: $repo_path"
        if ! aws ecr describe-repositories --repository-names "$repo_path" >/dev/null 2>&1; then
            echo "📁 Creating ECR repository: $repo_path"
            aws ecr create-repository --repository-name "$repo_path" >/dev/null
            echo "✅ Created ECR repository: $repo_path"
        else
            echo "✅ ECR repository already exists: $repo_path"
        fi
    }
    ensure_repo "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
    ensure_repo "$DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER"
fi

make_env_specific() {
    local image_name="$1"
    local clean="${image_name%\"}"
    clean="${clean#\"}"
    if [[ "$clean" == *:* ]]; then
        local base="${clean%:*}"
        local tag="${clean#*:}"
        printf "%s:%s-%s" "$base" "$tag" "$ENV_NAME"
    else
        printf "%s:%s" "$clean" "$ENV_NAME"
    fi
}

ENV_SPECIFIC_MINER_IMAGE_NAME="$(make_env_specific "$DOCKER_IMAGE_NAME_WHATSAPP_MINER")"
ENV_SPECIFIC_CLASSIFIER_IMAGE_NAME="$(make_env_specific "$DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER")"

echo "🔨 Building Docker images for environment: $ENV_NAME"
echo "   Miner:       base=$DOCKER_IMAGE_NAME_WHATSAPP_MINER -> env=$ENV_SPECIFIC_MINER_IMAGE_NAME"
echo "   Classifier:  base=$DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER -> env=$ENV_SPECIFIC_CLASSIFIER_IMAGE_NAME"

# Export the environment-specific image names for docker-compose
export DOCKER_IMAGE_NAME_WHATSAPP_MINER="$ENV_SPECIFIC_MINER_IMAGE_NAME"
export DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER="$ENV_SPECIFIC_CLASSIFIER_IMAGE_NAME"
export ENV_NAME="$ENV_NAME"

# Set up environment variables that docker-compose needs
export ENV_FILE="${ENV_FILE:-/tmp/whatsapp_miner.$$.env}"

# Build using docker-compose
echo "🔨 Building with docker-compose (both services)..."
docker compose build miner classifier

# Also tag with the base name for compatibility (using clean name)
echo "🏷️  Tagging with base names for compatibility..."
docker tag "$ENV_SPECIFIC_MINER_IMAGE_NAME" "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
docker tag "$ENV_SPECIFIC_CLASSIFIER_IMAGE_NAME" "${DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER%\"}"

if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "📤 Pushing miner image(s) to registry..."
    docker push "$ENV_SPECIFIC_MINER_IMAGE_NAME"
    docker push "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
    echo "📤 Pushing classifier image(s) to registry..."
    docker push "$ENV_SPECIFIC_CLASSIFIER_IMAGE_NAME"
    docker push "${DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER%\"}"
    echo "✅ Images pushed successfully"
fi

# Export the environment-specific image names for use by other scripts
export DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV="$ENV_SPECIFIC_MINER_IMAGE_NAME"
export DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER_ENV="$ENV_SPECIFIC_CLASSIFIER_IMAGE_NAME"
