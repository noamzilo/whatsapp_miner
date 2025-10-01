#!/usr/bin/env bash
# Helper script to load .env and run docker compose with env vars available
# This ensures env vars are available both for compose file substitution AND containers

set -euo pipefail

ENV_FILE="${1:-.env}"
shift

# Make ENV_FILE absolute if it isn't already
if [[ "$ENV_FILE" != /* ]]; then
    ENV_FILE="$(pwd)/$ENV_FILE"
fi

# Export ENV_FILE so compose can use it for ${ENV_FILE} substitution
export ENV_FILE

# Quote values with spaces for safe sourcing
# This converts: KEY=value with spaces
# To: KEY="value with spaces"
temp_env=$(mktemp)
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Quote the value if it contains spaces
    if [[ "$value" =~ [[:space:]] ]]; then
        echo "${key}=\"${value}\""
    else
        echo "${key}=${value}"
    fi
done < "$ENV_FILE" > "$temp_env"

# Export all vars from processed env file
set -a
source "$temp_env"
set +a

# Cleanup
rm -f "$temp_env"

# Run docker compose (ENV_FILE is already exported and absolute)
exec docker compose "$@"

