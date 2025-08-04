#!/usr/bin/env python3
"""
Verify Database Reset State

This script checks the current state of lead-related data in the database
to verify that a reset was successful.
"""

import sys
from pathlib import Path

# Add project root to Python path for relative imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.db.db import (
    get_db_session, get_total_messages_count, get_processed_messages_count,
    get_unprocessed_messages_count, get_leads_count, get_classifications_count,
    get_categories_count
)
from src.utils.log import get_logger, setup_logger

# Setup logging
setup_logger(project_root / "logs")
logger = get_logger(__name__)


def verify_database_state():
    """Check the current state of lead-related data in the database."""
    logger.info("🔍 Verifying database state...")
    
    try:
        with get_db_session() as session:
            # Count various entities
            total_messages = get_total_messages_count(session)
            processed_messages = get_processed_messages_count(session)
            unprocessed_messages = get_unprocessed_messages_count(session)
            
            total_leads = get_leads_count(session)
            total_classifications = get_classifications_count(session)
            total_categories = get_categories_count(session)
            
            logger.info("")
            logger.info("📊 DATABASE STATE:")
            logger.info(f"   📝 Total messages: {total_messages}")
            logger.info(f"   ✅ Processed messages: {processed_messages}")
            logger.info(f"   ⏳ Unprocessed messages: {unprocessed_messages}")
            logger.info(f"   🎯 Detected leads: {total_leads}")
            logger.info(f"   📊 Classifications: {total_classifications}")
            logger.info(f"   🏷️  Lead categories: {total_categories}")
            
            # Check if reset was successful
            if processed_messages == 0 and total_leads == 0 and total_classifications == 0 and total_categories == 0:
                logger.info("")
                logger.info("✅ RESET VERIFICATION: Database is in clean state!")
                logger.info("   - No messages are marked as processed")
                logger.info("   - No detected leads exist")
                logger.info("   - No classifications exist")
                logger.info("   - No lead categories exist")
            else:
                logger.info("")
                logger.warning("⚠️  RESET VERIFICATION: Database may not be fully reset")
                if processed_messages > 0:
                    logger.warning(f"   - {processed_messages} messages are still marked as processed")
                if total_leads > 0:
                    logger.warning(f"   - {total_leads} detected leads still exist")
                if total_classifications > 0:
                    logger.warning(f"   - {total_classifications} classifications still exist")
                if total_categories > 0:
                    logger.warning(f"   - {total_categories} lead categories still exist")
                    
    except Exception as e:
        logger.error(f"❌ Error verifying database state: {e}")
        raise


def main():
    """Main function to verify database state."""
    logger.info("🔍 Database State Verification")
    logger.info("=" * 50)
    
    try:
        verify_database_state()
        
    except Exception as e:
        logger.error(f"❌ Failed to verify database state: {e}")
        raise


if __name__ == "__main__":
    main() 