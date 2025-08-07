#!/usr/bin/env bash
# deploy_with_act.sh
# Deploy using Act (GitHub Actions locally) with Doppler secrets
set -euo pipefail

USER_ID=$(id -u)
GROUP_ID=$(getent group docker | cut -d: -f3)

# Prefer GitHub Container Registry; fallback to Docker Hub
PRIMARY_RUNNER_IMAGE="ghcr.io/catthehacker/ubuntu:act-latest"
FALLBACK_RUNNER_IMAGE="catthehacker/ubuntu:act-latest"
RUNNER_IMAGE="$PRIMARY_RUNNER_IMAGE"

pull_runner_image() {
  local image="$1"
  echo "📥 Pulling Act runner image: $image"
  if ! docker pull "$image"; then
    echo "⚠️  Pull failed for $image — attempting docker logout and retry..."
    local registry
    registry="${image%%/*}"
    # If image is like 'catthehacker/ubuntu:act-latest' (Docker Hub), registry would be entire repo
    # 'docker logout' without registry clears default creds
    if [[ "$image" == ghcr.io/* ]]; then
      docker logout ghcr.io || true
    else
      docker logout || true
    fi
    docker pull "$image"
  fi
}

# Parse arguments
TEST_MODE=false
if [[ "${1:-}" == "--test" ]]; then
    TEST_MODE=true
    echo "🧪 Test mode enabled (with timeout protection)"
fi

echo "🚀 Deploying with Act (GitHub Actions locally)..."
echo "   Using Doppler secrets for environment variables"

# Auto-setup Act runner image on first run
echo "🔧 Checking Act runner image..."
if docker image inspect "$PRIMARY_RUNNER_IMAGE" >/dev/null 2>&1; then
  RUNNER_IMAGE="$PRIMARY_RUNNER_IMAGE"
  echo "✅ Found runner image locally: $RUNNER_IMAGE"
elif docker image inspect "$FALLBACK_RUNNER_IMAGE" >/dev/null 2>&1; then
  RUNNER_IMAGE="$FALLBACK_RUNNER_IMAGE"
  echo "✅ Found runner image locally: $RUNNER_IMAGE"
else
  echo "📥 Runner image not found locally; downloading..."
  echo "   This may take 2-5 minutes on first run"
  echo "   Image size: ~1.5GB"
  if pull_runner_image "$PRIMARY_RUNNER_IMAGE"; then
    RUNNER_IMAGE="$PRIMARY_RUNNER_IMAGE"
    echo "✅ Act runner ready: $RUNNER_IMAGE"
  else
    echo "⚠️  Primary registry failed; trying Docker Hub mirror..."
    pull_runner_image "$FALLBACK_RUNNER_IMAGE"
    RUNNER_IMAGE="$FALLBACK_RUNNER_IMAGE"
    echo "✅ Act runner ready: $RUNNER_IMAGE"
  fi
fi

if [[ "$TEST_MODE" == "true" ]]; then
    echo "   Test mode: 10-minute timeout enabled"
    echo "   Press Ctrl+C to cancel if it takes too long"
    echo ""
    
    # Run Act with timeout in test mode
    timeout 600 bash -c '
echo "🔄 Starting Act deployment with timeout..."
doppler secrets download --project whatsapp_miner_backend --config dev_personal --no-file --format env \
	| sed "s/^/-s /" \
	| xargs act \
		-P ubuntu-latest='"$RUNNER_IMAGE"' \
		--container-options "-u '"$USER_ID:$GROUP_ID"'" \
		--reuse \
		--pull=false \
		-W .github/workflows/deploy.yml
'
    
    EXIT_CODE=$?
    
    if [[ $EXIT_CODE -eq 124 ]]; then
        echo ""
        echo "⏰ Act deployment timed out after 10 minutes"
        echo "   This is normal for the first run when downloading the runner image"
        echo "   Try running again without --test flag - subsequent runs will be much faster"
        exit 1
    elif [[ $EXIT_CODE -eq 0 ]]; then
        echo ""
        echo "✅ Act deployment completed successfully!"
    else
        echo ""
        echo "❌ Act deployment failed with exit code: $EXIT_CODE"
        exit $EXIT_CODE
    fi
else
    echo "   Normal mode: No timeout (may take several minutes on first run)"
    echo "   Press Ctrl+C to cancel if it hangs"
    echo ""
    
    # Run Act normally with reuse flag to prevent force pull
    doppler secrets download --project whatsapp_miner_backend --config dev_personal --no-file --format env \
	| sed 's/^/-s /' \
	| xargs act \
		-P ubuntu-latest="$RUNNER_IMAGE" \
		--container-options "-u $USER_ID:$GROUP_ID" \
		--reuse \
		--pull=false \
		-W .github/workflows/deploy.yml
fi

echo ""
echo "✅ Act deployment completed!"
