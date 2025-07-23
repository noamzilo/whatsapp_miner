#!/bin/bash

set -e

doppler secrets download --no-file --format docker > .env.doppler
docker run --rm --env-file .env.doppler whatsapp-miner -d
rm .env.doppler
