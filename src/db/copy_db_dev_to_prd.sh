#!/usr/bin/env bash
set -euo pipefail

PROJECT="whatsapp_miner_backend"
DEV_CONFIG="dev"
PRD_CONFIG="prd"
DUMP_FILE="whatsapp_miner_dump_public.dump"

# Get connection strings
DEV_DB_URL=$(doppler run --project "$PROJECT" --config "$DEV_CONFIG" -- bash -c 'echo "$SUPABASE_DATABASE_CONNECTION_STRING"')
PRD_DB_URL=$(doppler run --project "$PROJECT" --config "$PRD_CONFIG" -- bash -c 'echo "$SUPABASE_DATABASE_CONNECTION_STRING"')

# Dump only public schema
pg_dump "$DEV_DB_URL" \
	--clean \
	--if-exists \
	--no-owner \
	--no-privileges \
	--format=custom \
	--schema=public \
	--file="$DUMP_FILE"

# Restore only public schema
pg_restore \
	--no-owner \
	--no-privileges \
	--schema=public \
	--dbname="$PRD_DB_URL" \
	"$DUMP_FILE"
