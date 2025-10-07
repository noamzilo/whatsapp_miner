#!/bin/bash
set -e

# Restore from latest production snapshot if available
SNAPSHOT_DIR="/docker-entrypoint-initdb.d/snapshots"
SNAPSHOT="$SNAPSHOT_DIR/latest_prod_dump.backup"

if [ -s "$SNAPSHOT" ]; then
  echo "📥 Restoring database from snapshot: $SNAPSHOT"
  # Ensure authentication works during init when password auth is required
  export PGPASSWORD="${POSTGRES_PASSWORD}"
  # Allow pg_restore to continue even if optional Supabase extensions are missing locally
  set +e
  pg_restore --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$SNAPSHOT"
  RESTORE_EXIT_CODE=$?
  set -e
  if [ "$RESTORE_EXIT_CODE" -ne 0 ]; then
    echo "⚠️ Restore completed with non-fatal errors (likely missing extensions such as pg_graphql/supabase_vault)."
  else
    echo "✅ Restore complete"
  fi
else
  echo "⚠️ No valid snapshot found, starting with empty DB. Expected at: $SNAPSHOT"
fi


