#!/usr/bin/env bash
# Build, push, migrate & start the stack (both CI & local)

set -euo pipefail

########## 1.  Un-bundle secrets (if provided) ############################
if [[ -n "${DEPLOY_ENV_B64:-}" ]]; then
    tmp_json=$(mktemp)
    printf '%s' "$DEPLOY_ENV_B64" | base64 -d >"$tmp_json"
    # turn JSON → KEY=value lines → export
    while IFS='=' read -r k v; do export "$k"="$v"; done \
        < <(jq -r 'to_entries|map("\(.key)=\(.value|tostring)")|.[]' "$tmp_json")
    rm -f "$tmp_json"
fi
###########################################################################

########## 2.  Parse CLI --------------------------------------------------
ENVIRONMENT=dev
while [[ $# -gt 0 ]]; do
  case $1 in
    --env) ENVIRONMENT="$2"; shift 2;;
    *) echo "Usage: $0 --env dev|prd"; exit 1;;
  esac
done
[[ "$ENVIRONMENT" =~ ^(dev|prd)$ ]] || { echo "❌ bad env"; exit 1; }
echo "🌍 Environment: $ENVIRONMENT"

########## 3.  Guard – we expect these to be present now ------------------
: "${AWS_EC2_REGION:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

# map AWS creds for CLI
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_EC2_REGION}"

########## 4.  Business as before ----------------------------------------
echo "🔍 Validating deployment setup..."
./docker_validate_setup.sh --env "$ENVIRONMENT"

echo "🔨 Building & pushing image..."
./docker_build.sh --env "$ENVIRONMENT" --push
ENV_SPECIFIC_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV:-$DOCKER_IMAGE_NAME_WHATSAPP_MINER}"
NEW_IMAGE_DIGEST="$(docker images --digests --format 'table {{.Repository}}:{{.Tag}}\t{{.Digest}}' | grep "$ENV_SPECIFIC_IMAGE_NAME" | awk '{print $2}')"
echo "📦 New image digest: $NEW_IMAGE_DIGEST"

DIGEST_FILE="$(mktemp)"
echo "$NEW_IMAGE_DIGEST" >"$DIGEST_FILE"
export DIGEST_FILE_PATH="$DIGEST_FILE"

echo "🗄️  Running migrations…"
./run_migrations.sh --env "$ENVIRONMENT"

echo "🚀 Deploying…"
./docker_run.sh --env "$ENVIRONMENT" --remote

echo "📊 Final status:"
./docker_verify_deployment.sh --env "$ENVIRONMENT"
rm -f "$DIGEST_FILE_PATH"

echo -e "\n✅ Deployment complete ($ENVIRONMENT)\n"
