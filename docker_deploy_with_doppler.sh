#!/usr/bin/env bash
# Local helper: wrap Doppler secrets into one blob & forward to docker_deploy.sh
set -euo pipefail

# Ensure we are inside a Doppler context
if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
  exec doppler run --preserve-env -- "$0" "$@"
fi

# Collect ALL secrets as JSON → base64
SECRETS_B64=$(doppler secrets download --no-file --format json | base64 -w0)
echo "🔒 Packed $(echo -n "$SECRETS_B64" | wc -c) bytes of secrets"

# Never echo the blob itself!

chmod +x ./docker_deploy.sh
./docker_deploy.sh --secrets-b64 "$SECRETS_B64"
