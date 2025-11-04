# Sync Messages from Stage to Dev

This document describes the message syncing functionality that upserts messages from the stage database into the dev database.

## Overview

The sync script (`src/db/utils/sync_messages_from_stage.py`) copies messages and their dependencies from the stage environment to the dev environment. It uses upsert operations to handle duplicates intelligently.

## What Gets Synced

The script syncs the following in order:

1. **WhatsApp Users** (by `whatsapp_id`)
2. **WhatsApp Groups** (by `whatsapp_group_id`)
3. **WhatsApp Messages** (by `message_id`)
4. **Lead Categories** (by `name`) - optional
5. **Tagger Types** (by `name`) - optional
6. **Taggers** (by `tagger_type_id` + `identifier`) - optional
7. **Message Tags** (by `message_id` + `tagger_id` + `tagged_at`) - optional

The script handles:
- Foreign key relationships (users, groups, quoted messages)
- Duplicate prevention using unique constraints
- Updates to existing records
- Dry run mode for testing

## Usage

### Basic Sync

Sync all messages from stage to dev:

```bash
make sync-messages-stg-to-dev
```

### Dry Run

Check what would be synced without making changes:

```bash
make sync-messages-stg-to-dev-dry-run
```

### With Limit

Sync only a specific number of messages (useful for testing):

```bash
make sync-messages-stg-to-dev LIMIT=100
make sync-messages-stg-to-dev-dry-run LIMIT=10
```

## How It Works

### Database Connections

The Makefile extracts connection strings from **two separate** Doppler configs:
1. Runs `doppler run --config stg` to get stage DB connection string
2. Runs `doppler run --config dev` to get dev DB connection string
3. Passes both as `SOURCE_DB` and `TARGET_DB` to the Python script

The script itself does **not** run inside Doppler context - it uses **table reflection** to load table structures directly from the databases, avoiding the need to import models that would trigger `env_var_injection.py`.

### Table Reflection

The script uses SQLAlchemy's **table reflection** feature to load table structures:
- No model imports needed (avoids `env_var_injection.py` issues)
- Works with two separate database connections simultaneously
- Tables are loaded on-demand from the database schema

```python
source_users = Table('whatsapp_users', source_meta, autoload_with=source_session.bind)
target_users = Table('whatsapp_users', target_meta, autoload_with=target_session.bind)
```

### Upsert Strategy

For each entity:

1. Reflect table structure from both databases
2. Fetch all records from source database
3. For each record:
   - Map foreign key IDs using previously created mappings
   - Execute PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`
   - Store ID mapping (source ID → target ID)
4. Commit transaction

### Special Handling

**Quoted Messages**: Messages are upserted in two passes:
1. First pass: Insert/update messages without `quoted_message_id`
2. Second pass: Update `quoted_message_id` references using ID mappings

This avoids foreign key constraint violations when the quoted message hasn't been inserted yet.

## Environment Variables

The script accepts these environment variables:

- `SOURCE_DB` (required): Source database connection string
- `TARGET_DB` (required): Target database connection string
- `LIMIT` (optional): Maximum number of messages to sync
- `DRY_RUN` (optional): Set to "true" to preview without changes

Note: The Makefile commands handle these automatically via Doppler.

## Error Handling

- **Connection errors**: Script exits with error message
- **Missing dependencies**: Foreign key mappings handle missing references
- **Tag sync errors**: Tagged as warnings (tags are optional)

## Examples

### Full sync
```bash
make sync-messages-stg-to-dev
```

Output:
```
🔄 Syncing Messages from Stage to Dev
================================================================================
🔌 Connecting to databases...
   ✓ Connected to source (stage)
   ✓ Connected to target (dev)

📥 Syncing users...
   Found 45 users in source database
   ✓ Upserted 45 users

📥 Syncing groups...
   Found 12 groups in source database
   ✓ Upserted 12 groups

📥 Syncing messages...
   Found 1523 messages in source database
   ✓ Upserted 1523 messages (first pass - without quoted_message_id)
   ✓ Updated 89 quoted_message_id references

📥 Syncing tagger types...
   Found 2 tagger types in source database
   ✓ Upserted 2 tagger types

📥 Syncing taggers...
   Found 3 taggers in source database
   ✓ Upserted 3 taggers

📥 Syncing message tags...
   Found 234 message tags in source database
   ✓ Upserted 234 message tags

================================================================================
✓ Sync complete!
================================================================================
```

### Dry run with limit
```bash
make sync-messages-stg-to-dev-dry-run LIMIT=50
```

Output:
```
🔄 Syncing Messages from Stage to Dev
================================================================================
⚠ DRY RUN MODE - No changes will be made
📊 Limit: 50 messages

📥 Syncing users...
   Found 45 users in source database
   [DRY RUN] Would upsert 45 users

📥 Syncing groups...
   Found 12 groups in source database
   [DRY RUN] Would upsert 12 groups

📥 Syncing messages...
   Found 50 messages in source database (limited to 50)
   [DRY RUN] Would upsert 50 messages

================================================================================
✓ Dry run complete - no changes were made
================================================================================
```

## Integration with Makefile

The sync commands are integrated into the Makefile under the "Database Sync" section.

### How the Makefile Handles Two Doppler Configs

The Makefile cleverly extracts connection strings from **two separate** Doppler environments:

```makefile
sync-messages-stg-to-dev:
	# Step 1: Extract stage DB connection string
	@STG_DB=$$(doppler run --project whatsapp_miner_backend --config stg \
		--command 'echo $$SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER') && \
	
	# Step 2: Extract dev DB connection string
	DEV_DB=$$(doppler run --project whatsapp_miner_backend --config dev \
		--command 'echo $$SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER') && \
	
	# Step 3: Pass both to Python script (NOT inside Doppler)
	SOURCE_DB="$$STG_DB" TARGET_DB="$$DEV_DB" poetry run python -m src.db.utils.sync_messages_from_stage
```

Key points:
- Each `doppler run` is a separate subprocess that only echoes the connection string
- The script runs **outside** of Doppler context with just the two connection strings
- No env_var_injection issues because we use table reflection instead of model imports

## Testing

1. Start with a dry run to see what would be synced:
   ```bash
   make sync-messages-stg-to-dev-dry-run LIMIT=10
   ```

2. Test with a small limit:
   ```bash
   make sync-messages-stg-to-dev LIMIT=10
   ```

3. Verify the data in dev database:
   ```bash
   make psql-dev
   ```
   ```sql
   SELECT COUNT(*) FROM whatsapp_messages;
   ```

4. Run full sync:
   ```bash
   make sync-messages-stg-to-dev
   ```

## Troubleshooting

### "Missing required environment variable: SOURCE_DB"
- The Makefile should handle this automatically
- If running directly, ensure both SOURCE_DB and TARGET_DB are set

### "Could not sync message tags: ..."
- This is usually okay - tags may not exist in stage
- The warning can be safely ignored if you don't use tags

### Foreign key constraint violations
- Should not happen due to proper ordering
- If it does, check that all parent tables are synced first

### Duplicate key violations
- Should not happen due to ON CONFLICT DO UPDATE
- If it does, check unique constraints in migration files

## Notes

- The script preserves `message_id`, not database `id` (auto-increment)
- Existing messages are updated, not duplicated
- The sync is idempotent - safe to run multiple times
- Tags and taggers are optional and won't fail the entire sync

