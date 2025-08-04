#!/usr/bin/env bash
# docker_deploy_with_doppler.sh
# Local deployment: build, push, run migrations, and restart the container.
# Usage: ./docker_deploy_with_doppler.sh [--env dev|prd]

set -euo pipefail

# Source utility functions
source "$(dirname "$0")/docker_utils.sh"



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

echo "🌍 Environment: $ENVIRONMENT"

# ── Re-exec inside Doppler if not already ───────────────────────────────────
if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
	echo "🔄 Re-executing with Doppler context..."
	exec doppler run --preserve-env -- "$0" "$@"
fi

# ── Unquote Doppler variables ───────────────────────────────────────────────
unquote_doppler_vars

# ── Map AWS credentials ──────────────────────────────────────────────────────
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"

# ── Validate deployment setup ────────────────────────────────────────────────
echo "🔍 Validating deployment setup..."
./docker_validate_setup.sh --env "$ENVIRONMENT"

# ── Build and push image ────────────────────────────────────────────────────
echo "🔨 Building and pushing image..."

./docker_build.sh --env "$ENVIRONMENT" --push

# ── Get image digest for verification ───────────────────────────────────────
NEW_IMAGE_DIGEST="$(docker images --digests --format "table {{.Repository}}:{{.Tag}}\t{{.Digest}}" | grep "$DOCKER_IMAGE_NAME_WHATSAPP_MINER" | awk '{print $2}')"
echo "📦 New image digest: $NEW_IMAGE_DIGEST"
export NEW_IMAGE_DIGEST

# ── Run migrations for the specified environment ────────────────────────────
echo "🗄️  Running database migrations for environment: $ENVIRONMENT"
./run_migrations.sh --env "$ENVIRONMENT"

# ── Start services ───────────────────────────────────────────────────────────
echo "🚀 Starting services..."
./docker_run.sh --env "$ENVIRONMENT"

# ── Show final status ───────────────────────────────────────────────────────
echo "📊 Final deployment status:"
./docker_show_status.sh --env "$ENVIRONMENT"

echo ""
echo "🚀✅ DONE: WhatsApp Miner deployment completed successfully ✅🚀"
echo "   Environment: $ENVIRONMENT"
echo "   New image digest: $NEW_IMAGE_DIGEST"
echo ""
