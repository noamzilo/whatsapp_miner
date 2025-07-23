#!/bin/bash

set -e

IMAGE_NAME=$(doppler secrets get DOCKER_IMAGE_NAME_WHATSAPP_MINER --plain)
docker ps -q --filter "ancestor=$IMAGE_NAME" | xargs -r docker rm -f
doppler secrets download --no-file --format docker > .env.doppler
docker run --rm --env-file .env.doppler "$IMAGE_NAME"

rm .env.doppler