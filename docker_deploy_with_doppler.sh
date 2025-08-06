#!/usr/bin/env bash
# Local helper: wrap Doppler secrets into one blob & forward to docker_deploy.sh
set -euo pipefail

ENVIRONMENT=dev
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) ENVIRONMENT="$2"; shift 2;;
    *)     echo "Usage: $0 [--env dev|prd]"; exit 1;;
  esac
done

echo "🌍 Local Doppler deploy (env=$ENVIRONMENT)"

# Ensure we are inside a Doppler context
if [[ -z "${DOPPLER_PROJECT:-}" ]]; then
  exec doppler run --preserve-env -- "$0" "$@"
fi

# Collect ALL secrets as JSON → base64
SECRETS_B64=$(doppler secrets download --no-file --format json | base64 -w0)
echo "🔒 Packed $(echo -n "$SECRETS_B64" | wc -c) bytes of secrets"

# Never echo the blob itself!

chmod +x ./docker_deploy.sh
./docker_deploy.sh --env "$ENVIRONMENT" --secrets-b64 "$SECRETS_B64"
