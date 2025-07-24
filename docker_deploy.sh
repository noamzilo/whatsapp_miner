#!/bin/bash
set -euo pipefail

eval "$(doppler secrets download --no-file --format env)"
: "${AWS_EC2_REGION:?}"
aws ecr get-login-password --region "$AWS_EC2_REGION" \
	| docker login --username AWS --password-stdin "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

./docker_build.sh
docker push "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

./docker_run.sh --remote
