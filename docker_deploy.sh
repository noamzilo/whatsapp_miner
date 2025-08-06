#!/usr/bin/env bash
# Build, push, migrate, deploy. Secrets may be supplied as a single base-64 blob.
set -euo pipefail

###############################################################################
# ── argument parsing ─────────────────────────────────────────────────────────
###############################################################################
ENVIRONMENT=dev           # default
SECRETS_B64=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)          ENVIRONMENT="$2";      shift 2;;
    --secrets-b64)  SECRETS_B64="$2";      shift 2;;
    --*)            echo "❌ Unknown flag $1"; exit 1;;
    *)              echo "❌ Unexpected arg $1"; exit 1;;
  esac
done

if [[ ! "$ENVIRONMENT" =~ ^(dev|prd)$ ]]; then
  echo "❌ --env must be dev or prd"; exit 1
fi

###############################################################################
# ── secret bundle decoding (if provided) ─────────────────────────────────────
###############################################################################
if [[ -n "$SECRETS_B64" ]]; then
  tmp_json="$(mktemp)"
  printf '%s' "$SECRETS_B64" | base64 -d > "$tmp_json"

  # Each entry becomes KEY=VALUE and is exported
  while IFS='=' read -r k v; do
    export "$k"="$v"
  done < <(jq -r 'to_entries[] | "\(.key)=\(.value|tostring)"' "$tmp_json")

  rm -f "$tmp_json"
fi

###############################################################################
# ── original script logic (unchanged) ────────────────────────────────────────
###############################################################################
echo "🌍 Environment: $ENVIRONMENT"

: "${AWS_EC2_REGION:?}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?}"

export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_EC2_REGION}"

echo "🔍 Validating deployment setup…"
./docker_validate_setup.sh --env "$ENVIRONMENT"

echo "🔨 Building & pushing image…"
./docker_build.sh --env "$ENVIRONMENT" --push

ENV_SPECIFIC_IMAGE_NAME="${DOCKER_IMAGE_NAME_WHATSAPP_MINER_ENV:-$DOCKER_IMAGE_NAME_WHATSAPP_MINER}"
NEW_IMAGE_DIGEST=$(docker images --digests --format 'table {{.Repository}}:{{.Tag}}\t{{.Digest}}' |
                   grep "$ENV_SPECIFIC_IMAGE_NAME" | awk '{print $2}')
echo "📦 Image digest: $NEW_IMAGE_DIGEST"

DIGEST_FILE=$(mktemp /tmp/whatsapp_miner_digest.XXXX)
echo "$NEW_IMAGE_DIGEST" > "$DIGEST_FILE"
export DIGEST_FILE_PATH="$DIGEST_FILE"

echo "🗄️  Running migrations…"
./run_migrations.sh --env "$ENVIRONMENT"

echo "🚀 Deploying to remote host…"
./docker_run.sh --env "$ENVIRONMENT" --remote

echo "📊 Final status:"
./docker_verify_deployment.sh --env "$ENVIRONMENT"

rm -f "$DIGEST_FILE_PATH"
echo -e "\n✅ Deployment finished!"
