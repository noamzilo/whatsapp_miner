#!/usr/bin/env bash
# src/scripts/reset_db.sh
# Reset the database schema and re-run migrations via run_migrations.sh
# Usage: ./reset_db.sh --env <doppler-config>

set -euo pipefail

exit(1) # we don't want this to run my mistake. Be deliberate and comment this line if you really want.

# Parse arguments
ENV_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --env <doppler-config>"
            exit 1
            ;;
    esac
done

if [[ -z "$ENV_NAME" ]]; then
    echo "❌ Error: --env parameter is required"
    echo "Usage: $0 --env <doppler-config>"
    exit 1
fi

# Resolve DB URL for the requested environment
SUPABASE_DB_URL=$(doppler secrets --project whatsapp_miner_backend --config "$ENV_NAME" get SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER  --plain)

echo "⚠️  You are about to RESET the database:"
echo "    $(echo "$SUPABASE_DB_URL" | sed -E 's/:[^:@]+@/:***@/')"

read -p "Type RESET to continue: " confirm
if [ "$confirm" != "RESET" ]; then
    echo "Aborted."
    exit 1
fi

# Drop and recreate schema
echo "🗑️  Dropping schema 'public'..."
psql "$SUPABASE_DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Run alembic migrations through the unified script
echo "🚀 Running alembic migrations via src/scripts/run_migrations.sh..."
"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_migrations.sh" --env "$ENV_NAME"

# Check that alembic_version exists
echo "🔍 Verifying alembic_version table..."
if ! psql "$SUPABASE_DB_URL" -c "SELECT version_num FROM alembic_version;" >/dev/null 2>&1; then
    echo "❌ ERROR: alembic_version table not found — migrations didn’t apply!"
    exit 1
fi

# Check that at least one table exists (besides alembic_version)
TABLE_COUNT=$(psql "$SUPABASE_DB_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name != 'alembic_version';" | xargs)
if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No application tables created — migrations may have run but produced nothing."
    exit 1
fi

echo "✅ Database reset and migrations applied successfully!"
