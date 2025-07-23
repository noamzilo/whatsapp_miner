#!/bin/bash

set -e

# Inject all secrets into env
eval "$(doppler secrets download --no-file --format env)"

# Constants from environment
HOST="$AWS_EC2_HOST_ADDRESS"
KEY_B64="$AWS_EC2_PEM_CHATBOT_SA_B64"
IMAGE_NAME="$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
REGION="$AWS_EC2_REGION"
USER="$AWS_EC2_USERNAME"

# Docker login + push
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${IMAGE_NAME%/*}"
./docker_build.sh
docker push "$IMAGE_NAME"

# Temporary PEM key
KEY_FILE=$(mktemp)
echo "$KEY_B64" | base64 -d > "$KEY_FILE"
chmod 400 "$KEY_FILE"

# SSH into EC2 and deploy
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$USER@$HOST" << 'EOF'
	set -e
	cd whatsapp_miner_backend

	# Load Doppler secrets on remote side
	eval "\$(doppler secrets download --no-file --format env)"

	# Pull and run
	aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"
	docker pull "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

	./docker_run.sh
EOF

# Clean up
rm "$KEY_FILE"
