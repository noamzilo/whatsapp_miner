#!/bin/bash
# Migration Service Entrypoint
# Runs database migrations conditionally based on RUN_MIGRATIONS flag

set -e

echo "Migration service starting..."
echo "Script: /db/run_migration_and_exit.sh"
echo "Current directory: $(pwd)"
echo "RUN_MIGRATIONS value: ${RUN_MIGRATIONS:-not_set}"

# Check if migrations should be run
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations..."
    cd /app
    echo "🔧 Checking alembic syntax..."
    poetry run python -c "import alembic" || (echo "❌ SYNTAX ERROR in alembic import" && exit 1)
    echo "✅ Alembic import check passed"
    poetry run alembic upgrade head
    echo "Migrations completed successfully"
else
    echo "Skipping migrations (RUN_MIGRATIONS=false)"
fi

echo "Migration service exiting successfully"
exit 0