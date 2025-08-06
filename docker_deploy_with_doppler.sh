#!/usr/bin/env bash
# Local helper – wrap docker_deploy.sh but inject Doppler secrets
set -euo pipefail

ENVIRONMENT=dev
while [[ $# -gt 0 ]]; do
  case $1 in --env) ENVIRONMENT="$2"; shift 2;; *) echo "Usage: $0 --env dev|prd"; exit 1;; esac
done

# Relaunch inside Doppler (so $DOPPLER_* is set)
if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
  exec doppler run --preserve-env -- "$0" "$@"
fi

# Grab **all** secrets as JSON ➜ base64 ➜ export
DEPLOY_ENV_B64=$(
  doppler secrets download --no-file --format json | base64 -w0
)
export DEPLOY_ENV_B64

# Continue exactly like CI
exec ./docker_deploy.sh --env "$ENVIRONMENT"
