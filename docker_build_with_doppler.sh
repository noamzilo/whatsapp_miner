#!/usr/bin/env bash
# docker_build_with_doppler.sh
# Local wrapper: inject secrets with Doppler, then call the core builder.
# Usage: ./docker_build_with_doppler.sh [--push]
set -euo pipefail

doppler run --project whatsapp_miner_backend --config dev_personal --command "./docker_build.sh $*"
