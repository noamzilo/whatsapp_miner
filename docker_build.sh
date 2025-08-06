#!/usr/bin/env bash
# docker_build.sh
# Build the Docker image using docker-compose and env-injected name.
# Usage: ./docker_build.sh [--env dev|prd] [--push]
set -euo pipefail

: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# Parse arguments
PUSH_IMAGE=false
ENVIRONMENT="dev"  # Default to dev

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd] [--push]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'. Must be dev or prd"
    exit 1
fi

# If pushing, ensure we have AWS credentials and authenticate with ECR
if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "🔐 Setting up ECR authentication for push..."
    
    # Map IAM → AWS CLI (works for both Doppler and GitHub Actions)
    export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID}"
    export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY}"
    
    # Map region variable (works for both Doppler and GitHub Actions)
    export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_EC2_REGION}"
    
    # Validate required AWS variables
    : "${AWS_ACCESS_KEY_ID:?}"
    : "${AWS_SECRET_ACCESS_KEY:?}"
    : "${AWS_DEFAULT_REGION:?}"
    
    # Get ECR registry from cleaned image name
    CLEAN_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER%\"}"
    CLEAN_IMAGE_NAME="${CLEAN_IMAGE_NAME#\"}"
    ECR_REGISTRY="${CLEAN_IMAGE_NAME%/*}"
    
    # Create AWS credential files in a writable location
    echo "🔍 Debug: Creating AWS credential directory..."
    AWS_CREDS_DIR="/tmp/aws_creds_$$"
    echo "🔍 Debug: AWS_CREDS_DIR = $AWS_CREDS_DIR"
    
    echo "🔍 Debug: Creating directory..."
    mkdir -p "$AWS_CREDS_DIR"
    echo "🔍 Debug: Directory created successfully"
    
    echo "🔍 Debug: Setting directory permissions..."
    chmod 700 "$AWS_CREDS_DIR"
    echo "🔍 Debug: Directory permissions set"
    
    export AWS_SHARED_CREDENTIALS_FILE="$AWS_CREDS_DIR/credentials"
    export AWS_CONFIG_FILE="$AWS_CREDS_DIR/config"
    
    echo "🔍 Debug: AWS_SHARED_CREDENTIALS_FILE = $AWS_SHARED_CREDENTIALS_FILE"
    echo "🔍 Debug: AWS_CONFIG_FILE = $AWS_CONFIG_FILE"
    
    # Create the credential files with proper content
    echo "🔍 Debug: Creating credentials file..."
    cat > "$AWS_SHARED_CREDENTIALS_FILE" << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF
    echo "🔍 Debug: Credentials file created"
    
    echo "🔍 Debug: Creating config file..."
    cat > "$AWS_CONFIG_FILE" << EOF
[default]
region = $AWS_DEFAULT_REGION
output = json
EOF
    echo "🔍 Debug: Config file created"
    
    echo "🔍 Debug: Setting file permissions..."
    chmod 600 "$AWS_SHARED_CREDENTIALS_FILE" "$AWS_CONFIG_FILE"
    echo "🔍 Debug: File permissions set"
    
    # Login to ECR using credential files
    echo "🔐 Logging into ECR registry: $ECR_REGISTRY"
    
    echo "🔍 Debug: About to run AWS CLI..."
    echo "🔍 Debug: Command: aws ecr get-login-password --region $AWS_DEFAULT_REGION"
    
    # Use AWS CLI with the credential files
    echo "🔍 Debug: Running AWS CLI to get ECR password..."
    ECR_PASSWORD=$(aws ecr get-login-password --region "$AWS_DEFAULT_REGION")
    echo "🔍 Debug: AWS CLI completed, password length: ${#ECR_PASSWORD}"
    
    echo "🔍 Debug: About to run docker login..."
    echo "🔍 Debug: Docker login command: docker login --username AWS --password-stdin $ECR_REGISTRY"
    
    # Configure Docker to use a writable location for credentials
    DOCKER_CONFIG_DIR="/tmp/docker_config_$$"
    mkdir -p "$DOCKER_CONFIG_DIR"
    chmod 700 "$DOCKER_CONFIG_DIR"
    export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"
    
    echo "🔍 Debug: DOCKER_CONFIG = $DOCKER_CONFIG"
    
    # Use AWS CLI with the credential files
    echo "$ECR_PASSWORD" | docker login --username AWS --password-stdin "$ECR_REGISTRY"
    
    echo "🔍 Debug: Docker login command completed"
    
    # Clean up Docker config
    rm -rf "$DOCKER_CONFIG_DIR"
    
    # Clean up credential files
    echo "🔍 Debug: Cleaning up credential files..."
    rm -rf "$AWS_CREDS_DIR"
    echo "🔍 Debug: Cleanup completed"
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
    ENV_SPECIFIC_IMAGE_NAME="${BASE_IMAGE_NAME}:${BASE_TAG}-${ENVIRONMENT}"
else
    # No tag - append environment as tag
    ENV_SPECIFIC_IMAGE_NAME="${CLEAN_IMAGE_NAME}:${ENVIRONMENT}"
fi

echo "🔨 Building Docker image: $ENV_SPECIFIC_IMAGE_NAME"
echo "🌍 Environment: $ENVIRONMENT"
echo "   Base image: $DOCKER_IMAGE_NAME_WHATSAPP_MINER"
echo "   Environment-specific: $ENV_SPECIFIC_IMAGE_NAME"

# Export the environment-specific image name for docker-compose
export DOCKER_IMAGE_NAME_WHATSAPP_MINER="$ENV_SPECIFIC_IMAGE_NAME"
export ENVIRONMENT="$ENVIRONMENT"

# Set up environment variables that docker-compose needs
export ENV_NAME="$ENVIRONMENT"
export ENV_FILE="${ENV_FILE:-/tmp/whatsapp_miner.$$.env}"

# Build using docker-compose
echo "🔨 Building with docker-compose..."
docker compose build

# Also tag with the base name for compatibility (using clean name)
echo "🏷️  Tagging with base name for compatibility..."
docker tag "$ENV_SPECIFIC_IMAGE_NAME" "$CLEAN_IMAGE_NAME"

if [[ "$PUSH_IMAGE" == "true" ]]; then
    echo "📤 Pushing environment-specific image to registry..."
    
    # Debug: Check if ECR repository exists
    echo "🔍 Debug: Checking if ECR repository exists..."
    REPO_NAME="${CLEAN_IMAGE_NAME#*/}"
    echo "🔍 Debug: Repository name: $REPO_NAME"
    
    # Check if repository exists
    if aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$AWS_DEFAULT_REGION" >/dev/null 2>&1; then
        echo "🔍 Debug: ECR repository exists"
    else
        echo "🔍 Debug: ECR repository does not exist, creating it..."
        aws ecr create-repository --repository-name "$REPO_NAME" --region "$AWS_DEFAULT_REGION"
        echo "🔍 Debug: ECR repository created"
    fi
    
    docker push "$ENV_SPECIFIC_IMAGE_NAME"
    echo "📤 Pushing base image to registry..."
    docker push "$CLEAN_IMAGE_NAME"
    echo "✅ Images pushed successfully"
fi

# Export the environment-specific image name for use by other scripts
export DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV="$ENV_SPECIFIC_IMAGE_NAME"
