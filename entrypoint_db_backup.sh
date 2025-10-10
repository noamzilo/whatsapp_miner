#!/bin/bash
set -e

export TZ=America/Bogota
echo "Starting database backup service..."

perform_backup() {
    TIMESTAMP=$(date +%F_%H-%M-%S)
    echo "Starting backup at $(date)"
    BACKUP_FILE="/tmp/db_backup_${TIMESTAMP}.dump"
    echo "Creating database dump..."
    pg_dump "${SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER}" -Fc -Z9 > "$BACKUP_FILE"
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "s3://whatsapp-miner-backups/whatsapp_db_${TIMESTAMP}.dump"
    rm "$BACKUP_FILE"
    echo "Backup completed successfully at $(date)"
}

get_seconds_until_midnight() {
    local now=$(date +%s)
    local midnight=$(date -d "tomorrow 00:00" +%s)
    echo $((midnight - now))
}

echo "Waiting until midnight for first backup..."
sleep $(get_seconds_until_midnight)
perform_backup

while true; do
    echo "Waiting 24 hours for next backup..."
    sleep 86400
    perform_backup
done
