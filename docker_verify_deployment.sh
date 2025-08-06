#!/usr/bin/env bash
# docker_verify_deployment.sh
# Verifies that containers are actually running after deployment
# Usage: ./docker_verify_deployment.sh [--env dev|prd]
# Returns: 0 if containers are running, 1 if not

set -euo pipefail

# Parse arguments
ENVIRONMENT="dev"  # Default to dev

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'. Must be dev or prd"
    exit 1
fi

echo "🔍 Verifying deployment for environment: $ENVIRONMENT"

# Check if we're in GitHub Actions or local environment
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "🏗️  Running verification in GitHub Actions environment"
    # GitHub Actions: use environment variables directly
    : "${AWS_EC2_HOST_ADDRESS:?}"
    : "${AWS_EC2_USERNAME:?}"
    : "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
    : "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"
    
    # AWS variables are already set from GitHub secrets
    : "${AWS_ACCESS_KEY_ID:?}"
    : "${AWS_SECRET_ACCESS_KEY:?}"
    : "${AWS_DEFAULT_REGION:?}"
else
    # Local: check if we're in Doppler context, if not, re-exec with Doppler
    if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
        echo "🔄 Re-executing with Doppler context..."
        exec doppler run --preserve-env -- "$0" "$@"
    fi

    # ── Map AWS variables from Doppler to standard names ─────────────────────
    export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
    export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

    # ── Required variables (now mapped from Doppler) ─────────────────────────
    : "${AWS_EC2_HOST_ADDRESS:?}"
    : "${AWS_EC2_USERNAME:?}"
    : "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
    : "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"
fi

REMOTE_DIR="$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"

# Prepare SSH key
KEY_FILE="$(mktemp)"
echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
chmod 600 "$KEY_FILE"
trap 'rm -f "$KEY_FILE"' EXIT INT TERM

ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }

echo "🌐 Remote Host: $AWS_EC2_HOST_ADDRESS"
echo "📁 Remote Directory: $REMOTE_DIR"

# Create temp env file on remote with all variables
REMOTE_ENV="/tmp/whatsapp_miner_verify.$RANDOM.env"
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    env | ssh_cmd "cat > '$REMOTE_ENV'"
else
    doppler secrets download --no-file --format docker | ssh_cmd "cat > '$REMOTE_ENV'"
fi

# Function to check if containers are running
check_containers() {
    echo "🔍 Checking if containers are running..."
    
    # Get running containers
    RUNNING_CONTAINERS="$(ssh_cmd "docker ps --filter 'name=whatsapp_miner' --format '{{.Names}}'")"
    
    if [[ -z "$RUNNING_CONTAINERS" ]]; then
        echo "❌ No containers are running!"
        return 1
    fi
    
    echo "✅ Found running containers:"
    echo "$RUNNING_CONTAINERS" | while read -r container; do
        if [[ -n "$container" ]]; then
            echo "   - $container"
        fi
    done
    
    # Check if docker-compose services are running
    echo "🔍 Checking docker-compose services..."
    COMPOSE_STATUS="$(ssh_cmd "cd '$REMOTE_DIR' && set -a && source '$REMOTE_ENV' && set +a && ENV_FILE='$REMOTE_ENV' ENV_NAME='$ENVIRONMENT' docker compose ps --services --filter status=running")"
    
    if [[ -z "$COMPOSE_STATUS" ]]; then
        echo "❌ No docker-compose services are running!"
        return 1
    fi
    
    echo "✅ Docker-compose services running:"
    echo "$COMPOSE_STATUS" | while read -r service; do
        if [[ -n "$service" ]]; then
            echo "   - $service"
        fi
    done
    
    # Check that ALL expected services are running
    echo "🔍 Verifying all expected services are running..."
    EXPECTED_SERVICES="miner classifier"
    MISSING_SERVICES=""
    
    for expected_service in $EXPECTED_SERVICES; do
        if ! echo "$COMPOSE_STATUS" | grep -q "^${expected_service}$"; then
            MISSING_SERVICES="$MISSING_SERVICES $expected_service"
        fi
    done
    
    if [[ -n "$MISSING_SERVICES" ]]; then
        echo "❌ Missing expected services:$MISSING_SERVICES"
        echo "   Expected: miner classifier"
        echo "   Running: $COMPOSE_STATUS"
        return 1
    fi
    
    echo "✅ All expected services are running (miner, classifier)"
    
    # Check container health (basic check)
    echo "🔍 Checking container health..."
    for service in $COMPOSE_STATUS; do
        if [[ -n "$service" ]]; then
            CONTAINER_STATUS="$(ssh_cmd "cd '$REMOTE_DIR' && set -a && source '$REMOTE_ENV' && set +a && ENV_FILE='$REMOTE_ENV' ENV_NAME='$ENVIRONMENT' docker compose ps -q '$service' | xargs -r docker inspect --format '{{.State.Status}}'")"
            
            if [[ "$CONTAINER_STATUS" != "running" ]]; then
                echo "❌ Service $service is not running (status: $CONTAINER_STATUS)"
                return 1
            else
                echo "   ✅ $service is running"
            fi
        fi
    done
    
    return 0
}

# Main verification
if check_containers; then
    echo ""
    echo "✅ Deployment verification successful!"
    echo "   All containers are running and healthy"
    ssh_cmd "rm -f '$REMOTE_ENV'"
    exit 0
else
    echo ""
    echo "❌ Deployment verification failed!"
    echo "   Containers are not running properly"
    
    # Show debug information
    echo ""
    echo "🔍 Debug information:"
    echo "   Remote directory contents:"
    ssh_cmd "ls -la '$REMOTE_DIR'"
    echo ""
    echo "   All containers (including stopped):"
    ssh_cmd "docker ps -a --filter 'name=whatsapp_miner'"
    echo ""
    echo "   Docker-compose status:"
    ssh_cmd "cd '$REMOTE_DIR' && set -a && source '$REMOTE_ENV' && set +a && ENV_FILE='$REMOTE_ENV' ENV_NAME='$ENVIRONMENT' docker compose ps"
    echo ""
    echo "   Recent logs:"
    ssh_cmd "cd '$REMOTE_DIR' && set -a && source '$REMOTE_ENV' && set +a && ENV_FILE='$REMOTE_ENV' ENV_NAME='$ENVIRONMENT' docker compose logs --tail 50"
    
    ssh_cmd "rm -f '$REMOTE_ENV'"
    exit 1
fi 