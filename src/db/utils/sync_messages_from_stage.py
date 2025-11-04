#!/usr/bin/env python3
"""
Sync Messages from Stage to Dev Database

This script upserts messages from the stage database into the dev database.
It handles dependencies (users, groups) and uses message_id as the unique key
to avoid duplicates.

Usage:
    SOURCE_DB="..." TARGET_DB="..." python -m src.db.utils.sync_messages_from_stage

Environment Variables:
    SOURCE_DB: Connection string for source database (stage)
    TARGET_DB: Connection string for target database (dev)
    LIMIT: Optional limit on number of messages to sync (default: all)
    DRY_RUN: If set to "true", only print what would be synced without making changes

Note: This script uses table reflection to avoid importing models that trigger
env_var_injection.py. It's designed to work with two separate database connections.
"""

import os
import sys
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from typing import Dict, Any, List


def get_connection_strings():
    """Get source and target database connection strings from environment."""
    source_db = os.getenv("SOURCE_DB")
    target_db = os.getenv("TARGET_DB")
    
    if not source_db:
        raise RuntimeError("SOURCE_DB environment variable is required")
    if not target_db:
        raise RuntimeError("TARGET_DB environment variable is required")
    
    return source_db, target_db


def create_session(connection_string: str):
    """Create a database session from connection string."""
    engine = create_engine(connection_string)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal(), engine


def row_to_dict(row, exclude_cols: List[str] = None) -> Dict[str, Any]:
    """Convert SQLAlchemy row to dictionary."""
    exclude_cols = exclude_cols or []
    return {
        key: value
        for key, value in row._mapping.items()
        if key not in exclude_cols
    }


def upsert_users(source_session, target_session, source_meta, target_meta, dry_run: bool = False) -> Dict[int, int]:
    """
    Upsert users from source to target database.
    Returns mapping of source user IDs to target user IDs.
    """
    print("\n📥 Syncing users...")
    
    # Get table references
    source_users = Table('whatsapp_users', source_meta, autoload_with=source_session.bind)
    target_users = Table('whatsapp_users', target_meta, autoload_with=target_session.bind)
    
    # Fetch all users from source
    result = source_session.execute(select(source_users))
    users = result.fetchall()
    print(f"   Found {len(users)} users in source database")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(users)} users")
        return {}
    
    id_mapping = {}
    upserted_count = 0
    
    for user in users:
        user_data = row_to_dict(user, exclude_cols=['id', 'created_at'])
        
        # Upsert user (insert or update on conflict)
        stmt = insert(target_users).values(**user_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['whatsapp_id'],
            set_={
                'display_name': stmt.excluded.display_name,
            }
        ).returning(target_users.c.id)
        
        result = target_session.execute(stmt)
        target_id = result.scalar_one()
        id_mapping[user.id] = target_id
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} users")
    return id_mapping


def upsert_groups(source_session, target_session, source_meta, target_meta, dry_run: bool = False) -> Dict[int, int]:
    """
    Upsert groups from source to target database.
    Returns mapping of source group IDs to target group IDs.
    """
    print("\n📥 Syncing groups...")
    
    # Get table references
    source_groups = Table('whatsapp_groups', source_meta, autoload_with=source_session.bind)
    target_groups = Table('whatsapp_groups', target_meta, autoload_with=target_session.bind)
    
    # Fetch all groups from source
    result = source_session.execute(select(source_groups))
    groups = result.fetchall()
    print(f"   Found {len(groups)} groups in source database")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(groups)} groups")
        return {}
    
    id_mapping = {}
    upserted_count = 0
    
    for group in groups:
        group_data = row_to_dict(group, exclude_cols=['id', 'created_at'])
        
        # Upsert group (insert or update on conflict)
        stmt = insert(target_groups).values(**group_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['whatsapp_group_id'],
            set_={
                'group_name': stmt.excluded.group_name,
                'location_city': stmt.excluded.location_city,
                'location_neighbourhood': stmt.excluded.location_neighbourhood,
                'location': stmt.excluded.location,
            }
        ).returning(target_groups.c.id)
        
        result = target_session.execute(stmt)
        target_id = result.scalar_one()
        id_mapping[group.id] = target_id
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} groups")
    return id_mapping


def upsert_messages(
    source_session,
    target_session,
    source_meta,
    target_meta,
    user_id_mapping: Dict[int, int],
    group_id_mapping: Dict[int, int],
    limit: int = None,
    dry_run: bool = False
) -> Dict[int, int]:
    """
    Upsert messages from source to target database.
    Returns mapping of source message IDs to target message IDs.
    """
    print("\n📥 Syncing messages...")
    
    # Get table references
    source_messages = Table('whatsapp_messages', source_meta, autoload_with=source_session.bind)
    target_messages = Table('whatsapp_messages', target_meta, autoload_with=target_session.bind)
    
    # Fetch messages from source (with optional limit)
    query = select(source_messages).order_by(source_messages.c.id)
    if limit:
        query = query.limit(limit)
    
    result = source_session.execute(query)
    messages = result.fetchall()
    print(f"   Found {len(messages)} messages in source database{f' (limited to {limit})' if limit else ''}")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(messages)} messages")
        return {}
    
    id_mapping = {}
    
    # First pass: upsert messages without quoted_message_id
    # (to avoid foreign key issues when quoted message doesn't exist yet)
    upserted_count = 0
    
    for message in messages:
        message_data = row_to_dict(message, exclude_cols=['id', 'quoted_message_id'])
        
        # Map foreign keys
        if message.sender_id:
            message_data['sender_id'] = user_id_mapping.get(message.sender_id)
        if message.group_id:
            message_data['group_id'] = group_id_mapping.get(message.group_id)
        
        # Upsert message (insert or update on conflict)
        stmt = insert(target_messages).values(**message_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['message_id'],
            set_={
                'raw_text': stmt.excluded.raw_text,
                'message_type': stmt.excluded.message_type,
                'is_forwarded': stmt.excluded.is_forwarded,
                'timestamp': stmt.excluded.timestamp,
                'sender_id': stmt.excluded.sender_id,
                'group_id': stmt.excluded.group_id,
                'llm_processed': stmt.excluded.llm_processed,
                'is_real': stmt.excluded.is_real,
            }
        ).returning(target_messages.c.id)
        
        result = target_session.execute(stmt)
        target_id = result.scalar_one()
        id_mapping[message.id] = target_id
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} messages (first pass - without quoted_message_id)")
    
    # Second pass: update quoted_message_id references
    updated_count = 0
    for message in messages:
        if message.quoted_message_id is not None:
            target_message_id = id_mapping[message.id]
            target_quoted_message_id = id_mapping.get(message.quoted_message_id)
            
            if target_quoted_message_id:
                stmt = (
                    target_messages.update()
                    .where(target_messages.c.id == target_message_id)
                    .values(quoted_message_id=target_quoted_message_id)
                )
                target_session.execute(stmt)
                updated_count += 1
    
    target_session.commit()
    if updated_count > 0:
        print(f"   ✓ Updated {updated_count} quoted_message_id references")
    
    return id_mapping


def upsert_lead_categories(source_session, target_session, source_meta, target_meta, dry_run: bool = False) -> Dict[int, int]:
    """
    Upsert lead categories from source to target database.
    Returns mapping of source lead category IDs to target lead category IDs.
    """
    print("\n📥 Syncing lead categories...")
    
    try:
        # Get table references
        source_lead_categories = Table('lead_categories', source_meta, autoload_with=source_session.bind)
        target_lead_categories = Table('lead_categories', target_meta, autoload_with=target_session.bind)
    except Exception as e:
        print(f"   ⚠ Table not found: {e}")
        return {}
    
    # Fetch all lead categories from source
    result = source_session.execute(select(source_lead_categories))
    lead_categories = result.fetchall()
    print(f"   Found {len(lead_categories)} lead categories in source database")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(lead_categories)} lead categories")
        return {}
    
    id_mapping = {}
    upserted_count = 0
    
    for lead_category in lead_categories:
        lead_category_data = row_to_dict(lead_category, exclude_cols=['id'])
        
        # Upsert lead category (insert or update on conflict)
        stmt = insert(target_lead_categories).values(**lead_category_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['name'],
            set_={
                'description': stmt.excluded.description,
                'opening_message_template': stmt.excluded.opening_message_template,
            }
        ).returning(target_lead_categories.c.id)
        
        result = target_session.execute(stmt)
        target_id = result.scalar_one()
        id_mapping[lead_category.id] = target_id
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} lead categories")
    return id_mapping


def upsert_tagger_types(source_session, target_session, source_meta, target_meta, dry_run: bool = False) -> Dict[int, int]:
    """
    Upsert tagger types from source to target database.
    Returns mapping of source tagger type IDs to target tagger type IDs.
    """
    print("\n📥 Syncing tagger types...")
    
    try:
        # Get table references
        source_tagger_types = Table('tagger_types', source_meta, autoload_with=source_session.bind)
        target_tagger_types = Table('tagger_types', target_meta, autoload_with=target_session.bind)
    except Exception as e:
        print(f"   ⚠ Table not found: {e}")
        return {}
    
    # Fetch all tagger types from source
    result = source_session.execute(select(source_tagger_types))
    tagger_types = result.fetchall()
    print(f"   Found {len(tagger_types)} tagger types in source database")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(tagger_types)} tagger types")
        return {}
    
    id_mapping = {}
    upserted_count = 0
    
    for tagger_type in tagger_types:
        tagger_type_data = row_to_dict(tagger_type, exclude_cols=['id'])
        
        # Upsert tagger type (insert or update on conflict)
        stmt = insert(target_tagger_types).values(**tagger_type_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['name'],
            set_={
                'name': stmt.excluded.name,
            }
        ).returning(target_tagger_types.c.id)
        
        result = target_session.execute(stmt)
        target_id = result.scalar_one()
        id_mapping[tagger_type.id] = target_id
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} tagger types")
    return id_mapping


def upsert_taggers(
    source_session,
    target_session,
    source_meta,
    target_meta,
    tagger_type_id_mapping: Dict[int, int],
    dry_run: bool = False
) -> Dict[int, int]:
    """
    Upsert taggers from source to target database.
    Returns mapping of source tagger IDs to target tagger IDs.
    """
    print("\n📥 Syncing taggers...")
    
    try:
        # Get table references
        source_taggers = Table('taggers', source_meta, autoload_with=source_session.bind)
        target_taggers = Table('taggers', target_meta, autoload_with=target_session.bind)
    except Exception as e:
        print(f"   ⚠ Table not found: {e}")
        return {}
    
    # Fetch all taggers from source
    result = source_session.execute(select(source_taggers))
    taggers = result.fetchall()
    print(f"   Found {len(taggers)} taggers in source database")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(taggers)} taggers")
        return {}
    
    id_mapping = {}
    upserted_count = 0
    
    for tagger in taggers:
        tagger_data = row_to_dict(tagger, exclude_cols=['id'])
        
        # Map foreign key
        if tagger.tagger_type_id:
            tagger_data['tagger_type_id'] = tagger_type_id_mapping.get(tagger.tagger_type_id)
        
        # Upsert tagger (insert or update on conflict)
        stmt = insert(target_taggers).values(**tagger_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['tagger_type_id', 'identifier'],
            set_={
                'identifier': stmt.excluded.identifier,
            }
        ).returning(target_taggers.c.id)
        
        result = target_session.execute(stmt)
        target_id = result.scalar_one()
        id_mapping[tagger.id] = target_id
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} taggers")
    return id_mapping


def upsert_message_tags(
    source_session,
    target_session,
    source_meta,
    target_meta,
    message_id_mapping: Dict[int, int],
    tagger_id_mapping: Dict[int, int],
    lead_category_id_mapping: Dict[int, int],
    dry_run: bool = False
):
    """Upsert message tags from source to target database."""
    print("\n📥 Syncing message tags...")
    
    try:
        # Get table references
        source_tags = Table('message_tags', source_meta, autoload_with=source_session.bind)
        target_tags = Table('message_tags', target_meta, autoload_with=target_session.bind)
    except Exception as e:
        print(f"   ⚠ Table not found: {e}")
        return
    
    # Fetch all message tags from source
    result = source_session.execute(select(source_tags))
    tags = result.fetchall()
    print(f"   Found {len(tags)} message tags in source database")
    
    if dry_run:
        print(f"   [DRY RUN] Would upsert {len(tags)} message tags")
        return
    
    upserted_count = 0
    skipped_count = 0
    
    for tag in tags:
        # Map foreign keys
        target_message_id = message_id_mapping.get(tag.message_id)
        target_tagger_id = tagger_id_mapping.get(tag.tagger_id)
        
        if not target_message_id or not target_tagger_id:
            skipped_count += 1
            continue
        
        tag_data = row_to_dict(tag, exclude_cols=['id'])
        tag_data['message_id'] = target_message_id
        tag_data['tagger_id'] = target_tagger_id
        
        # Map lead_category_id if present
        if tag.lead_category_id:
            tag_data['lead_category_id'] = lead_category_id_mapping.get(tag.lead_category_id)
        
        # Upsert message tag (insert or update on conflict)
        # Unique constraint is (message_id, tagger_id, tagged_at)
        stmt = insert(target_tags).values(**tag_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['message_id', 'tagger_id', 'tagged_at'],
            set_={
                'is_lead': stmt.excluded.is_lead,
                'lead_category_id': stmt.excluded.lead_category_id,
                'confidence_score': stmt.excluded.confidence_score,
                'notes': stmt.excluded.notes,
            }
        )
        
        target_session.execute(stmt)
        upserted_count += 1
    
    target_session.commit()
    print(f"   ✓ Upserted {upserted_count} message tags")
    if skipped_count > 0:
        print(f"   ⚠ Skipped {skipped_count} tags (missing message or tagger mapping)")


def main():
    """Main function to sync messages from stage to dev."""
    # Parse environment variables
    source_db, target_db = get_connection_strings()
    limit = os.getenv("LIMIT")
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            print(f"⚠ Invalid LIMIT value: {limit}, ignoring", file=sys.stderr)
            limit = None
    
    print("=" * 80)
    print("🔄 Syncing Messages from Stage to Dev")
    print("=" * 80)
    if dry_run:
        print("⚠ DRY RUN MODE - No changes will be made")
    if limit:
        print(f"📊 Limit: {limit} messages")
    print()
    
    # Create database sessions
    print("🔌 Connecting to databases...")
    source_session, source_engine = create_session(source_db)
    target_session, target_engine = create_session(target_db)
    print("   ✓ Connected to source (stage)")
    print("   ✓ Connected to target (dev)")
    
    # Reflect database metadata
    source_meta = MetaData()
    target_meta = MetaData()
    
    try:
        # Sync dependencies first
        user_id_mapping = upsert_users(source_session, target_session, source_meta, target_meta, dry_run)
        group_id_mapping = upsert_groups(source_session, target_session, source_meta, target_meta, dry_run)
        
        # Sync messages
        message_id_mapping = upsert_messages(
            source_session,
            target_session,
            source_meta,
            target_meta,
            user_id_mapping,
            group_id_mapping,
            limit,
            dry_run
        )
        
        # Sync message tags (optional - may not exist in all environments)
        try:
            lead_category_id_mapping = upsert_lead_categories(source_session, target_session, source_meta, target_meta, dry_run)
            tagger_type_id_mapping = upsert_tagger_types(source_session, target_session, source_meta, target_meta, dry_run)
            tagger_id_mapping = upsert_taggers(
                source_session,
                target_session,
                source_meta,
                target_meta,
                tagger_type_id_mapping,
                dry_run
            )
            upsert_message_tags(
                source_session,
                target_session,
                source_meta,
                target_meta,
                message_id_mapping,
                tagger_id_mapping,
                lead_category_id_mapping,
                dry_run
            )
        except Exception as e:
            print(f"\n⚠ Warning: Could not sync message tags: {e}")
            print("   (This is okay if the tags tables don't exist or are empty)")
        
        print("\n" + "=" * 80)
        if dry_run:
            print("✓ Dry run complete - no changes were made")
        else:
            print("✓ Sync complete!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during sync: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        source_session.close()
        target_session.close()
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
