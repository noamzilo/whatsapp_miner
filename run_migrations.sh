#!/usr/bin/env bash
# run_migrations.sh
# Runs database migrations for the specified environment.
# Usage: ./run_migrations.sh [--env dev|prd]

set -euo pipefail

# Parse arguments
ENV_NAME="dev"  # Default to dev
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENV_NAME'. Must be dev or prd"
    exit 1
fi

echo "🗄️  Running database migrations for environment: $ENV_NAME"

# Check if we're in GitHub Actions or local environment
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "🏗️  Running migrations in GitHub Actions environment"
    : "${SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER:?}"
    echo "🔄 Running migrations for $ENV_NAME database..."
    alembic upgrade head
else
    echo "🌪️  Running migrations locally with Doppler"
    
    # Map environment to Doppler config
    case "$ENV_NAME" in
        "dev")
            DOPPLER_CONFIG="dev"
            ;;
        "prd")
            DOPPLER_CONFIG="prd"
            ;;
    esac
    
    echo "🔄 Running migrations for $ENV_NAME database (Doppler config: $DOPPLER_CONFIG)..."
    doppler run --project whatsapp_miner_backend --config "$DOPPLER_CONFIG" -- poetry run alembic upgrade head
fi

echo "✅ Database migrations completed successfully for environment: $ENV_NAME"