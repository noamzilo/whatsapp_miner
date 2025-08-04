#!/usr/bin/env python3
"""
Reset Lead Status in Database

This script resets the lead classification status by:
1. Setting all messages "llm_processed" to FALSE
2. Removing all leads
3. Removing all lead categories  
4. Removing all message_intent_classification rows

This is useful for testing the classification system from a clean state.
"""

import sys
import logging
from pathlib import Path
from typing import List

# Add project root to Python path for relative imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import paths for relative imports
from src.paths import project_root
from src.db.db import (
    get_db_session, update_messages_to_unprocessed, delete_all_leads,
    delete_all_classifications, delete_all_categories, get_processed_messages_count,
    get_leads_count, get_classifications_count, get_categories_count
)
from src.utils.log import get_logger, setup_logger

# Setup logging
setup_logger(project_root / "logs")
logger = get_logger(__name__)


def reset_lead_status_in_db():
    """Reset all lead-related data in the database."""
    logger.info("🔄 Starting database lead status reset...")
    
    try:
        with get_db_session() as session:
            # 1. Set all messages "llm_processed" to FALSE
            logger.info("📝 Resetting message processing status...")
            messages_updated = update_messages_to_unprocessed(session)
            session.commit()
            logger.info(f"✅ Updated {messages_updated} messages to unprocessed")
            
            # 2. Remove all leads
            logger.info("🗑️  Removing all detected leads...")
            leads_deleted = delete_all_leads(session)
            session.commit()
            logger.info(f"✅ Deleted {leads_deleted} detected leads")
            
            # 3. Remove all message_intent_classification rows
            logger.info("🗑️  Removing all message intent classifications...")
            classifications_deleted = delete_all_classifications(session)
            session.commit()
            logger.info(f"✅ Deleted {classifications_deleted} message intent classifications")
            
            # 4. Remove all lead categories
            logger.info("🗑️  Removing all lead categories...")
            categories_deleted = delete_all_categories(session)
            session.commit()
            logger.info(f"✅ Deleted {categories_deleted} lead categories")
            
            # 5. Verify the reset
            remaining_messages = get_processed_messages_count(session)
            remaining_leads = get_leads_count(session)
            remaining_classifications = get_classifications_count(session)
            remaining_categories = get_categories_count(session)
            
            logger.info("")
            logger.info("📊 RESET VERIFICATION:")
            logger.info(f"   📝 Messages still marked as processed: {remaining_messages}")
            logger.info(f"   🎯 Remaining detected leads: {remaining_leads}")
            logger.info(f"   📊 Remaining classifications: {remaining_classifications}")
            logger.info(f"   🏷️  Remaining lead categories: {remaining_categories}")
            
            if (remaining_messages == 0 and remaining_leads == 0 and 
                remaining_classifications == 0 and remaining_categories == 0):
                logger.info("✅ SUCCESS: Database has been completely reset!")
            else:
                logger.warning("⚠️  WARNING: Some data may not have been fully reset")
                
    except Exception as e:
        logger.error(f"❌ Error during database reset: {e}")
        raise


def main():
    """Main function to run the database reset."""
    logger.info("🚀 Starting Lead Status Reset Script")
    logger.info("=" * 50)
    
    try:
        reset_lead_status_in_db()
        logger.info("")
        logger.info("✅ Lead status reset completed successfully!")
        logger.info("🔄 The database is now ready for fresh classification testing")
        
    except Exception as e:
        logger.error(f"❌ Failed to reset lead status: {e}")
        raise


if __name__ == "__main__":
    main() 