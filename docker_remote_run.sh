#!/usr/bin/env bash
# docker_remote_run.sh
# Runs on EC2; forwards to docker_run_core.sh.

set -euo pipefail

: "${ENV_FILE:?}"  # passed in by docker_run.sh --remote

# Ensure ECR vars exist (they are re-computed inside docker_run_core.sh)
export IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
export AWS_ECR_REGISTRY="${IMAGE_NAME%/*}"
export AWS_ECR_LOGIN_PASSWORD="$(aws ecr get-login-password --region "$AWS_EC2_REGION")"

./docker_run_core.sh
