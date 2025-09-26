#!/usr/bin/env bash
# run_migrations.sh
# Run database migrations using Doppler for environment variable injection
# Usage: ./run_migrations.sh [command] [options]
# 
# Common commands:
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

# Default alembic command if none provided
ALEMBIC_COMMAND="${1:-upgrade head}"

# Shift to remove the first argument, leaving any additional options
shift 2>/dev/null || true
ALEMBIC_OPTIONS="$*"

echo "🚀 Running database migrations with Doppler..."
echo "📁 Project root: $PROJECT_ROOT"
echo "🔧 Alembic command: $ALEMBIC_COMMAND"
if [[ -n "$ALEMBIC_OPTIONS" ]]; then
    echo "⚙️  Additional options: $ALEMBIC_OPTIONS"
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

# Run alembic with Doppler environment injection
echo "🔄 Executing: doppler run --project whatsapp_miner_backend --config dev_personal --command \"alembic $ALEMBIC_COMMAND $ALEMBIC_OPTIONS\""
doppler run \
    --project whatsapp_miner_backend \
    --config dev_personal \
    --command "alembic $ALEMBIC_COMMAND $ALEMBIC_OPTIONS"

echo "✅ Migration command completed successfully!"
