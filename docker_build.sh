#!/usr/bin/env bash
# docker_build.sh
# Build the Docker image using docker-compose and env-injected name.
# Usage: ./docker_build.sh [--env dev|prd] [--push] [--image-name IMAGE_NAME] [--region REGION] [--pem-cert PEM_B64]
set -euo pipefail

# Parse arguments
PUSH_IMAGE=false
ENV_NAME="dev"  # Default to dev
DOCKER_IMAGE_NAME_WHATSAPP_MINER=""
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
            DOCKER_IMAGE_NAME_WHATSAPP_MINER="$2"
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

# Validate required arguments
if [[ -z "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" ]]; then
    echo "❌ Error: --image-name is required"
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
    
    # Get ECR registry from cleaned image name
    CLEAN_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
    CLEAN_IMAGE_NAME="${CLEAN_IMAGE_NAME#\"}"
    ECR_REGISTRY="${CLEAN_IMAGE_NAME%/*}"
    
    # Login to ECR
    echo "🔐 Logging into ECR registry: $ECR_REGISTRY"
    
    # Use AWS CLI to get ECR password (simpler approach that was working)
    ECR_PASSWORD=$(aws ecr get-login-password --region "$AWS_DEFAULT_REGION")
    
    # Login to Docker with ECR password
    echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
fi

# Create environment-specific image name
# Use tags to distinguish environments within the same repository
# Remove quotes from the image name if present
CLEAN_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
CLEAN_IMAGE_NAME="${CLEAN_IMAGE_NAME#\"}"

if [[ "$CLEAN_IMAGE_NAME" == *:* ]]; then
    # Has tag - extract base name and tag, then append environment to tag
    BASE_IMAGE_NAME="${CLEAN_IMAGE_NAME%:*}"
    BASE_TAG="${CLEAN_IMAGE_NAME#*:}"
    ENV_SPECIFIC_IMAGE_NAME="${BASE_IMAGE_NAME}:${BASE_TAG}-${ENV_NAME}"
else
    # No tag - append environment as tag
    ENV_SPECIFIC_IMAGE_NAME="${CLEAN_IMAGE_NAME}:${ENV_NAME}"
fi

echo "🔨 Building Docker image: $ENV_SPECIFIC_IMAGE_NAME"
echo "🌍 Environment: $ENV_NAME"
echo "   Base image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "   Environment-specific: $ENV_SPECIFIC_IMAGE_NAME"

# Export the environment-specific image name for docker-compose
export DOCKER_IMAGE_NAME_WHATSAPP_MINER="$ENV_SPECIFIC_IMAGE_NAME"
export ENV_NAME="$ENV_NAME"

# Set up environment variables that docker-compose needs
export ENV_FILE="${ENV_FILE:-/tmp/whatsapp_miner.$$.env}"

# Build using docker-compose
echo "🔨 Building with docker-compose..."
docker compose build

# Also tag with the base name for compatibility (using clean name)
echo "🏷️  Tagging with base name for compatibility..."
docker tag "$ENV_SPECIFIC_IMAGE_NAME" "$CLEAN_IMAGE_NAME"

if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "📤 Pushing environment-specific image to registry..."
    docker push "$ENV_SPECIFIC_IMAGE_NAME"
    echo "📤 Pushing base image to registry..."
    docker push "$CLEAN_IMAGE_NAME"
    echo "✅ Images pushed successfully"
fi

# Export the environment-specific image name for use by other scripts
export DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV="$ENV_SPECIFIC_IMAGE_NAME"
