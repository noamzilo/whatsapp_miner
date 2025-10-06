#!/bin/bash
# ════════════════════════════════════════════════════════════════════════════
# Migration Service Entrypoint
# Runs database migrations conditionally based on RUN_MIGRATIONS flag
# ════════════════════════════════════════════════════════════════════════════

set -e

echo "🔄 Migration service starting..."

# Check if migrations should be run
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "📦 Running database migrations..."
    cd /app
    poetry run alembic upgrade head
    echo "✅ Migrations completed successfully"
else
    echo "⏭️  Skipping migrations (RUN_MIGRATIONS=false)"
fi

echo "🏁 Migration service exiting successfully"
exit 0
