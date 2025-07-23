#!/bin/bash

set -e

IMAGE_NAME=$(doppler secrets get DOCKER_IMAGE_NAME_WHATSAPP_MINER --plain)
docker build -t "$IMAGE_NAME" .
