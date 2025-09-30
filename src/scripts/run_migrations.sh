#!/usr/bin/env bash
# src/scripts/run_migrations.sh
# Run database migrations using Doppler for environment variable injection
# Usage: ./run_migrations.sh --env <doppler-config> [alembic command and options]
# 
# Examples:
#   ./run_migrations.sh --env dev_personal                 # defaults to "upgrade head"
#   ./run_migrations.sh --env prd upgrade head             # run upgrade head on prod
#   ./run_migrations.sh --env dev_personal downgrade -1    # rollback one migration
# 
# Common Alembic commands:
#   upgrade head     - Apply all pending migrations (default)
#   downgrade -1     - Rollback one migration
#   current          - Show current migration version
#   history          - Show migration history
#   revision --autogenerate -m "message" - Create new migration
set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root (two levels up from scripts)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Parse arguments: --env <doppler-config> and collect remaining as Alembic command/options
ENV_NAME=""
CMD_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            if [[ $# -lt 2 ]]; then
                echo "❌ Error: --env requires a value"
                echo "Usage: $0 --env <doppler-config> [alembic command and options]"
                exit 1
            fi
            ENV_NAME="$2"
            shift 2
            ;;
        *)
            CMD_ARGS+=("$1")
            shift
            ;;
    esac
done

# Default alembic command if none provided
if [[ ${#CMD_ARGS[@]} -eq 0 ]]; then
    ALEMBIC_COMMAND="upgrade head"
else
    ALEMBIC_COMMAND="${CMD_ARGS[*]}"
fi

echo "🚀 Running database migrations with Doppler..."
echo "📁 Project root: $PROJECT_ROOT"
echo "🔧 Alembic command: $ALEMBIC_COMMAND"

# Ensure required flags
if [[ -z "$ENV_NAME" ]]; then
    echo "❌ Error: --env parameter is required"
    echo "Usage: $0 --env <doppler-config> [alembic command and options]"
    exit 1
fi

# Change to project root directory
cd "$PROJECT_ROOT"

# Check if alembic.ini exists
if [[ ! -f "alembic.ini" ]]; then
    echo "❌ Error: alembic.ini not found in project root"
    exit 1
fi

# Check if migrations directory exists
if [[ ! -d "migrations" ]]; then
    echo "❌ Error: migrations directory not found in project root"
    exit 1
fi

# Run alembic with Doppler environment injection using project virtual environment
echo "🔄 Executing: doppler run --project whatsapp_miner_backend --config $ENV_NAME --command \"source .venv/bin/activate && python -m alembic $ALEMBIC_COMMAND\""
doppler run \
    --project whatsapp_miner_backend \
    --config "$ENV_NAME" \
    --command "source .venv/bin/activate && python -m alembic $ALEMBIC_COMMAND"

echo "✅ Migration command completed successfully!"
