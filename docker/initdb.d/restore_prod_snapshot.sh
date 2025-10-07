#!/bin/bash
set -e

# Restore from latest production snapshot if available
SNAPSHOT_DIR="/docker-entrypoint-initdb.d/snapshots"
SNAPSHOT="$SNAPSHOT_DIR/latest_prod_dump.backup"

if [ -s "$SNAPSHOT" ]; then
  echo "📥 Restoring database from snapshot: $SNAPSHOT"
  # Ensure authentication works during init when password auth is required
  export PGPASSWORD="${POSTGRES_PASSWORD}"
  pg_restore --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$SNAPSHOT"
  echo "✅ Restore complete"
else
  echo "⚠️ No valid snapshot found, starting with empty DB. Expected at: $SNAPSHOT"
fi


