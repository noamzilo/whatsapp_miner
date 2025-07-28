#!/usr/bin/env bash
# Local wrapper: run deploy with Doppler-injected secrets.
set -euo pipefail

doppler run --command "./docker_deploy.sh"
