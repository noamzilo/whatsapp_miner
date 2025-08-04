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
from src.db.db_interface import get_db_session
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_classification import MessageIntentClassification
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
            messages_updated = session.query(WhatsAppMessage).filter(
                WhatsAppMessage.llm_processed == True
            ).update({"llm_processed": False})
            session.commit()
            logger.info(f"✅ Updated {messages_updated} messages to unprocessed")
            
            # 2. Remove all leads
            logger.info("🗑️  Removing all detected leads...")
            leads_deleted = session.query(DetectedLead).count()
            session.query(DetectedLead).delete()
            session.commit()
            logger.info(f"✅ Deleted {leads_deleted} detected leads")
            
            # 3. Remove all message_intent_classification rows
            logger.info("🗑️  Removing all message intent classifications...")
            classifications_deleted = session.query(MessageIntentClassification).count()
            session.query(MessageIntentClassification).delete()
            session.commit()
            logger.info(f"✅ Deleted {classifications_deleted} message intent classifications")
            
            # 4. Remove all lead categories
            logger.info("🗑️  Removing all lead categories...")
            categories_deleted = session.query(LeadCategory).count()
            session.query(LeadCategory).delete()
            session.commit()
            logger.info(f"✅ Deleted {categories_deleted} lead categories")
            
            # 5. Verify the reset
            remaining_messages = session.query(WhatsAppMessage).filter(
                WhatsAppMessage.llm_processed == True
            ).count()
            remaining_leads = session.query(DetectedLead).count()
            remaining_classifications = session.query(MessageIntentClassification).count()
            remaining_categories = session.query(LeadCategory).count()
            
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