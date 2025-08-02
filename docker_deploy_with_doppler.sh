#!/usr/bin/env bash
# docker_deploy_with_doppler.sh
# Local wrapper: run deploy with Doppler-injected secrets.
set -euo pipefail

doppler run --project whatsapp_miner_backend --config dev_personal --command "./docker_deploy.sh"
