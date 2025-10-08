#!/usr/bin/env python3
"""
Manual Database Changes Utility
Provides functions for manual database operations that require careful handling.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.db.db import get_db_session
from src.utils.log import get_logger

logger = get_logger(__name__)


def reset_llm_processed_flag(session: Optional[Session] = None, dry_run: bool = False) -> int:
    """
    Reset the llm_processed flag to False for all WhatsApp messages.
    
    Args:
        session: Database session to use. If None, creates a new session.
        dry_run: If True, only count affected records without making changes.
        
    Returns:
        Number of messages that were (or would be) affected.
    """
    if session is None:
        session = get_db_session()
        should_close_session = True
    else:
        should_close_session = False
    
    try:
        # First, count how many messages would be affected
        count_query = text("SELECT COUNT(*) FROM whatsapp_messages WHERE llm_processed = true")
        result = session.execute(count_query)
        affected_count = result.scalar()
        
        logger.info(f"📊 Found {affected_count} messages with llm_processed=true")
        
        if dry_run:
            logger.info("🔍 DRY RUN: No changes made")
            return affected_count
        
        if affected_count == 0:
            logger.info("✅ No messages need to be reset (all already have llm_processed=false)")
            return 0
        
        # Reset the flag for all messages
        update_query = text("UPDATE whatsapp_messages SET llm_processed = false WHERE llm_processed = true")
        result = session.execute(update_query)
        updated_count = result.rowcount
        
        # Commit the changes
        session.commit()
        
        logger.info(f"✅ Successfully reset llm_processed flag for {updated_count} messages")
        
        # Verify the change
        verify_query = text("SELECT COUNT(*) FROM whatsapp_messages WHERE llm_processed = true")
        result = session.execute(verify_query)
        remaining_count = result.scalar()
        
        if remaining_count == 0:
            logger.info("✅ Verification: All messages now have llm_processed=false")
        else:
            logger.warning(f"⚠️  Verification: {remaining_count} messages still have llm_processed=true")
        
        return updated_count
        
    except Exception as e:
        logger.error(f"❌ Error resetting llm_processed flag: {e}")
        session.rollback()
        raise
    finally:
        if should_close_session:
            session.close()


def get_llm_processed_stats(session: Optional[Session] = None) -> dict:
    """
    Get statistics about llm_processed flag status.
    
    Args:
        session: Database session to use. If None, creates a new session.
        
    Returns:
        Dictionary with statistics about processed vs unprocessed messages.
    """
    if session is None:
        session = get_db_session()
        should_close_session = True
    else:
        should_close_session = False
    
    try:
        # Get total count
        total_query = text("SELECT COUNT(*) FROM whatsapp_messages")
        result = session.execute(total_query)
        total_count = result.scalar()
        
        # Get processed count
        processed_query = text("SELECT COUNT(*) FROM whatsapp_messages WHERE llm_processed = true")
        result = session.execute(processed_query)
        processed_count = result.scalar()
        
        # Get unprocessed count
        unprocessed_count = total_count - processed_count
        
        stats = {
            'total_messages': total_count,
            'processed_messages': processed_count,
            'unprocessed_messages': unprocessed_count,
            'processed_percentage': (processed_count / total_count * 100) if total_count > 0 else 0
        }
        
        logger.info(f"📊 Message Processing Stats:")
        logger.info(f"   Total messages: {stats['total_messages']}")
        logger.info(f"   Processed: {stats['processed_messages']} ({stats['processed_percentage']:.1f}%)")
        logger.info(f"   Unprocessed: {stats['unprocessed_messages']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting llm_processed stats: {e}")
        raise
    finally:
        if should_close_session:
            session.close()


if __name__ == "__main__":
    import sys
    
    # Simple CLI interface
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        dry_run = len(sys.argv) > 2 and sys.argv[2] == "--dry-run"
        print(f"🔄 Resetting llm_processed flag for all messages (dry_run={dry_run})")
        affected = reset_llm_processed_flag(dry_run=dry_run)
        print(f"✅ Affected {affected} messages")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        print("📊 Getting llm_processed statistics...")
        stats = get_llm_processed_stats()
        print(f"📊 Stats: {stats}")
    else:
        print("Usage:")
        print("  python -m src.db.utils.manual_db_changes reset [--dry-run]")
        print("  python -m src.db.utils.manual_db_changes stats")
