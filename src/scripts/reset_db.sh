#!/usr/bin/env bash
set -euo pipefail

# Get connection string from Doppler
SUPABASE_DB_URL=$(doppler secrets --project whatsapp_miner_backend --config dev_personal get SUPABASE_DATABASE_CONNECTION_STRING --plain)
#SUPABASE_DB_URL=$(doppler secrets --project whatsapp_miner_backend --config prd get SUPABASE_DATABASE_CONNECTION_STRING --plain)

# Show connection details (only host + db name, not password)
echo "⚠️  You are about to RESET the database:"
echo "    URL: $SUPABASE_DB_URL" | sed -E 's/:[^:@]+@/:***@/'   # hide password

# Extra precaution: ask user to type RESET
read -p "Type RESET to continue: " confirm
if [ "$confirm" != "RESET" ]; then
	echo "Aborted."
	exit 1
fi

# Double-check with user
echo "Dropping and recreating schema 'public'..."
psql "$SUPABASE_DB_URL" -c "DROP SCHEMA public CASCADE;"
psql "$SUPABASE_DB_URL" -c "CREATE SCHEMA public;"

# Re-run migrations
echo "Running migrations..."
supabase db reset

echo "✅ Database has been reset and migrations reapplied."
