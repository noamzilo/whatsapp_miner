#!/bin/bash

set -euo pipefail

IMAGE_NAME=$(doppler secrets get DOCKER_IMAGE_NAME_WHATSAPP_MINER --plain)
docker build -t "$IMAGE_NAME" .
