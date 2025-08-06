#!/usr/bin/env bash
# docker_build_with_doppler.sh
# Local wrapper: inject secrets with Doppler, then call the core builder.
# Usage: ./docker_build_with_doppler.sh [--env dev|prd] [--push]
set -euo pipefail

# Source utility functions
source "$(dirname "$0")/docker_utils.sh"

# Unquote Doppler variables
unquote_doppler_vars

# Build the command with all required arguments
BUILD_ARGS="$*"

# Add required arguments from environment variables
if [[ "$BUILD_ARGS" == *"--push"* ]]; then
    # When pushing, we need all variables
    BUILD_ARGS="$BUILD_ARGS --image-name \"$DOCKER_IMAGE_NAME_WHATSAPP_MINER\" --region \"$AWS_EC2_REGION\" --access-key \"$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID\" --secret-key \"$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY\""
else
    # When not pushing, we only need image name
    BUILD_ARGS="$BUILD_ARGS --image-name \"$DOCKER_IMAGE_NAME_WHATSAPP_MINER\""
fi

doppler run --project whatsapp_miner_backend --config dev_personal --command "./docker_build.sh $BUILD_ARGS"
