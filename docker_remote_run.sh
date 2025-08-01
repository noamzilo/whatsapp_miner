#!/usr/bin/env bash
# docker_remote_run.sh
# Runs on EC2; forwards to docker_run_core.sh.

set -euo pipefail

: "${ENV_FILE:?}"  # passed in by docker_run.sh --remote

# ── Load every secret from the Doppler .env file ───────────────────────────
set -a
source "$ENV_FILE"
set +a

# ── Compute ECR parameters (env is now populated) ──────────────────────────
export IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
export AWS_ECR_REGISTRY="${IMAGE_NAME%/*}"
export AWS_ECR_LOGIN_PASSWORD="$(aws ecr get-login-password --region "$AWS_EC2_REGION")"

# Map Doppler creds (now present in ENV_FILE) to standard AWS vars
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

# Pass NEW_IMAGE_DIGEST to docker_run_core.sh if available
if [[ -n "${NEW_IMAGE_DIGEST:-}" ]]; then
    export NEW_IMAGE_DIGEST
fi

./docker_run_core.sh

# ── Verify deployment if NEW_IMAGE_DIGEST is provided ───────────────────────
if [[ -n "${NEW_IMAGE_DIGEST:-}" ]]; then
    echo "🔍 Verifying deployment..."
    sleep 10  # Give containers time to start
    
    # Check if new image is running
    REMOTE_IMAGE_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" | awk '{print $2}' || echo "")"
    
    if [[ "$REMOTE_IMAGE_DIGEST" != "$NEW_IMAGE_DIGEST" ]]; then
        echo "❌ Deployment verification failed!"
        echo "   Expected digest: $NEW_IMAGE_DIGEST"
        echo "   Remote digest:   $REMOTE_IMAGE_DIGEST"
        echo "   Remote containers:"
        docker ps -a || true
        exit 1
    fi
    
    echo "✅ Deployment verified - new image is running"
fi
