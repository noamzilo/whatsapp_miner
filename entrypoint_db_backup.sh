#!/bin/bash
set -euo pipefail

export TZ=America/Bogota
echo "Starting database backup service..."

# Every network call here is time-bounded on purpose. The 2026-03-19 outage was
# not a crash -- pg_dump (or the upload) stalled with no timeout, so the process
# hung forever. `set -e` never fired, the container never exited, and the restart
# policy never kicked in, so it sat "Up" and healthy-looking for 5 months while
# backing up nothing. A hang must look like a failure, or nobody finds out.
DUMP_TIMEOUT_SEC="${DUMP_TIMEOUT_SEC:-900}"
UPLOAD_TIMEOUT_SEC="${UPLOAD_TIMEOUT_SEC:-600}"
ATTEMPTS="${BACKUP_ATTEMPTS:-3}"
RETRY_DELAY_SEC="${RETRY_DELAY_SEC:-300}"
# Refuse to connect for more than a minute rather than blocking indefinitely.
export PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-60}"

attempt_backup() {
	TIMESTAMP=$(date +%F_%H-%M-%S)
	BACKUP_FILE="/tmp/db_backup_${TIMESTAMP}.dump"
	# Always clear the temp file, including on timeout, so a repeatedly failing
	# backup cannot fill the disk with half-written dumps.
	trap 'rm -f "$BACKUP_FILE"' RETURN

	echo "Starting backup at $(date)"
	if ! timeout --signal=TERM --kill-after=60 "$DUMP_TIMEOUT_SEC" \
		pg_dump "${SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER}" -Fc -Z9 > "$BACKUP_FILE"; then
		echo "❌ pg_dump failed or exceeded ${DUMP_TIMEOUT_SEC}s"
		return 1
	fi

	# A dump that is suspiciously small is a silent corruption, not a success.
	SIZE=$(stat -c %s "$BACKUP_FILE")
	if [ "$SIZE" -lt 100000 ]; then
		echo "❌ dump is only ${SIZE} bytes, refusing to upload it"
		return 1
	fi
	echo "Dump OK: ${SIZE} bytes. Uploading to S3..."

	if ! timeout --signal=TERM --kill-after=60 "$UPLOAD_TIMEOUT_SEC" \
		aws s3 cp "$BACKUP_FILE" "s3://whatsapp-miner-backups/whatsapp_db_${TIMESTAMP}.dump"; then
		echo "❌ upload failed or exceeded ${UPLOAD_TIMEOUT_SEC}s"
		return 1
	fi

	echo "✅ Backup completed successfully at $(date)"
	return 0
}

perform_backup() {
	for i in $(seq 1 "$ATTEMPTS"); do
		if attempt_backup; then
			return 0
		fi
		echo "attempt $i/$ATTEMPTS failed"
		[ "$i" -lt "$ATTEMPTS" ] && sleep "$RETRY_DELAY_SEC"
	done
	# Exit non-zero so docker's restart policy restarts us and the container is
	# visibly unhealthy, instead of failing quietly until someone looks in 5 months.
	echo "💀 all $ATTEMPTS attempts failed -- exiting so the container restarts"
	return 1
}

get_seconds_until_midnight() {
	local now midnight
	now=$(date +%s)
	midnight=$(date -d "tomorrow 00:00" +%s)
	echo $((midnight - now))
}

echo "Waiting until midnight for first backup..."
sleep "$(get_seconds_until_midnight)"
perform_backup

while true; do
	echo "Waiting until next midnight for the next backup..."
	# Sleep to the next midnight rather than a flat 86400: the old loop drifted
	# ~5s per day and would wander off its slot over months.
	sleep "$(get_seconds_until_midnight)"
	perform_backup
done
