#!/bin/bash

set -e

# Config - edit these as needed
AWS_REGION="us-east-1"
ECR_REPO_NAME="whatsapp-miner"
ECR_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"
EC2_USER="ubuntu"
EC2_HOST="your-ec2-public-dns"
DOCKER_IMAGE_NAME="whatsapp-miner"
REMOTE_IMAGE="$ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest"

# 1. Build the Docker image
./docker_build.sh

# 2. Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION \
	| docker login --username AWS --password-stdin $ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 3. Tag and push to ECR
docker tag $DOCKER_IMAGE_NAME:latest $REMOTE_IMAGE
docker push $REMOTE_IMAGE

echo "Image pushed to ECR: $REMOTE_IMAGE"

# 4. SSH to EC2, pull image, and run with Doppler injected
echo "Connecting to EC2: $EC2_USER@$EC2_HOST"

ssh $EC2_USER@$EC2_HOST bash -c "'
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker pull $REMOTE_IMAGE
doppler run -- bash -c \"docker run --rm \
	-e GREEN_API_INSTANCE_ID=\\\"\$GREEN_API_INSTANCE_ID\\\" \
	-e GREEN_API_INSTANCE_API_TOKEN=\\\"\$GREEN_API_INSTANCE_API_TOKEN\\\" \
	$REMOTE_IMAGE\"
'"
