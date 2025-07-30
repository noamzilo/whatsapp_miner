#!/usr/bin/env bash
# deploy_with_act.sh
# Deploy using Act (GitHub Actions locally) with Doppler secrets
set -euo pipefail

USER_ID=$(id -u)
GROUP_ID=$(getent group docker | cut -d: -f3)

# Parse arguments
TEST_MODE=false
if [[ "${1:-}" == "--test" ]]; then
    TEST_MODE=true
    echo "🧪 Test mode enabled (with timeout protection)"
fi

echo "🚀 Deploying with Act (GitHub Actions locally)..."
echo "   Using Doppler secrets for environment variables"

if [[ "$TEST_MODE" == "true" ]]; then
    echo "   Test mode: 10-minute timeout enabled"
    echo "   Press Ctrl+C to cancel if it takes too long"
    echo ""
    
    # Run Act with timeout in test mode
    timeout 600 bash -c '
echo "🔄 Starting Act deployment with timeout..."
doppler secrets download --no-file --format env \
	| sed "s/^/-s /" \
	| xargs act \
		-P ubuntu-latest=catthehacker/ubuntu:act-latest \
		--container-options "-u '"$USER_ID:$GROUP_ID"'" \
		--reuse \
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
    doppler secrets download --no-file --format env \
	| sed 's/^/-s /' \
	| xargs act \
		-P ubuntu-latest=catthehacker/ubuntu:act-latest \
		--container-options "-u $USER_ID:$GROUP_ID" \
		--reuse \
		-W .github/workflows/deploy.yml
fi

echo ""
echo "✅ Act deployment completed!"
