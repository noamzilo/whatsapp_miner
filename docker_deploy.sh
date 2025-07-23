#!/bin/bash

set -euo pipefail

# ────────────────────────────────────────────────────────────────
# Ensure tools are installed: aws, doppler, docker
# ────────────────────────────────────────────────────────────────

install_aws_cli() {
	if ! command -v aws >/dev/null; then
		echo "[INFO] Installing AWS CLI v2..."
		sudo apt-get update
		sudo apt-get install -y unzip
		curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
		unzip -q awscliv2.zip
		sudo ./aws/install
		rm -rf aws awscliv2.zip
	fi
}

install_doppler() {
	if ! command -v doppler >/dev/null; then
		echo "[INFO] Installing Doppler CLI..."
		curl -sLf --retry 3 --retry-delay 2 https://downloads.doppler.com/linux/latest | sh
		sudo mv doppler /usr/local/bin
	fi
}

install_docker() {
	if ! command -v docker >/dev/null; then
		echo "[INFO] Installing Docker..."
		sudo apt-get update
		sudo apt-get install -y \
			ca-certificates curl gnupg lsb-release
		sudo mkdir -p /etc/apt/keyrings
		curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
		echo \
			"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
			$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
		sudo apt-get update
		sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
	fi
}

install_git() {
	if ! command -v git >/dev/null; then
		echo "[INFO] Installing Git..."
		sudo apt-get update
		sudo apt-get install -y git
	fi
}

install_all_dependencies() {
	install_git
	install_docker
	install_doppler
	install_aws_cli
}

install_all_dependencies

# ────────────────────────────────────────────────────────────────
# Load Doppler secrets into env
# ────────────────────────────────────────────────────────────────

eval "$(doppler secrets download --no-file --format env)"

: "${AWS_EC2_HOST_ADDRESS:?Missing AWS_EC2_HOST_ADDRESS}"
: "${AWS_EC2_PEM_CHATBOT_SA_B64:?Missing AWS_EC2_PEM_CHATBOT_SA_B64}"
: "${DOCKER_IMAGE_NAME_WHATSAPP_MINER:?Missing DOCKER_IMAGE_NAME_WHATSAPP_MINER}"
: "${AWS_EC2_REGION:?Missing AWS_EC2_REGION}"
: "${AWS_EC2_USERNAME:?Missing AWS_EC2_USERNAME}"
: "${AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID:?Missing AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID}"
: "${AWS_IAM_WHATSAPP_MINER_ACCESS_KEY:?Missing AWS_IAM_WHATSAPP_MINER_ACCESS_KEY}"

# Map Doppler secrets to AWS standard variable names
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"

# ────────────────────────────────────────────────────────────────
# Build and push image
# ────────────────────────────────────────────────────────────────

echo "[INFO] Logging in to ECR and pushing image..."
aws ecr get-login-password --region "$AWS_EC2_REGION" \
	| docker login --username AWS --password-stdin "${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

./docker_build.sh
docker push "$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

# ────────────────────────────────────────────────────────────────
# SSH to EC2 and deploy remotely
# ────────────────────────────────────────────────────────────────

KEY_FILE=$(mktemp)
echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
chmod 400 "$KEY_FILE"

echo "[INFO] Connecting to EC2 and deploying..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" << 'EOF'
	set -euo pipefail

	# Create and enter working directory
	mkdir -p ~/whatsapp_miner
	cd ~/whatsapp_miner

	# Ensure Doppler and AWS CLI exist remotely
	if ! command -v doppler >/dev/null; then
		curl -sLf --retry 3 --retry-delay 2 https://downloads.doppler.com/linux/latest | sh
		sudo mv doppler /usr/local/bin
	fi

	if ! command -v aws >/dev/null || aws --version | grep -q 'aws-cli/1'; then
		sudo apt-get update
		sudo apt-get install -y unzip
		curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
		unzip -q awscliv2.zip
		sudo ./aws/install
		rm -rf aws awscliv2.zip
	fi

	# Load env vars
	eval "\$(doppler secrets download --no-file --format env)"

	# Docker login, pull, run
	aws ecr get-login-password --region "\$AWS_EC2_REGION" \
		| docker login --username AWS --password-stdin "\${DOCKER_IMAGE_NAME_WHATSAPP_MINER%/*}"

	docker pull "\$DOCKER_IMAGE_NAME_WHATSAPP_MINER"

	doppler secrets download --no-file --format docker > .env.doppler
	docker ps -q --filter "ancestor=\$DOCKER_IMAGE_NAME_WHATSAPP_MINER" | xargs -r docker rm -f
	docker run --rm --env-file .env.doppler "\$DOCKER_IMAGE_NAME_WHATSAPP_MINER"
	rm .env.doppler
EOF

echo "[INFO] Cleaning up..."
rm "$KEY_FILE"

echo "[SUCCESS] Deployment complete"
