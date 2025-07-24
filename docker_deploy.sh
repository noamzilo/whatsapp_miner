#!/bin/bash
set -euo pipefail

eval "$(doppler secrets download --no-file --format env)"
: "${AWS_EC2_REGION:?}"

export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

aws ecr get-login-password --region "$AWS_EC2_REGION" \
	| docker login --username AWS --password-stdin "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

./docker_build.sh
docker push "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

./docker_run.sh --remote
