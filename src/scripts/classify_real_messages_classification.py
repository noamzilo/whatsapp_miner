#!/usr/bin/env python3
"""
Script to test reading real messages from production database and classifying them.

This script reads 10 unclassified real messages from the production database,
classifies them using the real classifier, but writes results to the fake database
to keep the production database intact.

Usage:
    python src/scripts/test_real_messages_classification.py
"""

# Configuration: Set to True to write results to real database, False for fake database
USE_REAL_DATABASE = False

import sys
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.message_classification.message_classifier import MessageClassifier
from src.db.test_db import TestDatabase, TestDataFactory
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType
from src.db.db import (
    get_lead_statistics, get_detailed_lead_summary, get_processing_summary,
    create_fake_message_with_dependencies, get_unclassified_messages,
    mark_message_as_processed, create_classification_record, create_lead_record,
    get_or_create_lead_category, get_or_create_intent_type, get_classification_prompt,
    match_with_existing_categories
)
from src.db.db_interface import get_db_session
from src.utils.log import get_logger, setup_logger
from src.paths import logs_root

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


def read_real_unclassified_messages(db_read_limit: int = 50, result_limit: int = 10) -> List[Dict[str, Any]]:
    """Read real unclassified messages from production database."""
    
    logger.info(f"📖 Reading up to {db_read_limit} unclassified messages from production database...")
    
    messages = []
    try:
        with get_db_session() as session:
            # Get unclassified messages from real database
            unclassified_messages = session.query(WhatsAppMessage).filter(
                WhatsAppMessage.llm_processed == False
            ).limit(db_read_limit).all()
            
            logger.info(f"✅ Found {len(unclassified_messages)} unclassified messages in production database")
            
            # Convert to dictionary format for classifier and filter short messages
            for msg in unclassified_messages:
                # Skip messages under 8 characters
                if len(msg.raw_text.strip()) < 8:
                    logger.info(f"   ⏭️  Skipping short message {msg.id}: '{msg.raw_text[:20]}...' (length: {len(msg.raw_text)})")
                    continue
                
                messages.append({
                    'id': msg.id,
                    'raw_text': msg.raw_text,
                    'sender_id': msg.sender_id,
                    'group_id': msg.group_id,
                    'timestamp': msg.timestamp,
                    'real_message_id': msg.id  # Keep track of real message ID
                })
                
                logger.info(f"   📝 Message {msg.id}: '{msg.raw_text[:50]}...' (length: {len(msg.raw_text)})")
    
    except Exception as e:
        logger.error(f"❌ Error reading from production database: {e}")
        return []
    
    logger.info(f"✅ After filtering, processing {len(messages)} messages")
    return messages[:result_limit]


def create_fake_messages_from_real_data(real_messages: List[Dict[str, Any]], test_session) -> List[WhatsAppMessage]:
    """Create fake messages in test database based on real message data."""
    
    logger.info("🔄 Creating fake messages in test database from real data...")
    
    fake_messages = []
    for i, real_msg in enumerate(real_messages, 1):
        try:
            # Create fake message with same content but new IDs
            message_id = create_fake_message_with_dependencies(
                session=test_session,
                message_text=real_msg['raw_text'],
                user_id=real_msg['sender_id'],
                group_id=real_msg['group_id']
            )
            
            # Get the created message
            fake_message = test_session.query(WhatsAppMessage).filter_by(id=message_id).first()
            
            # Store real message ID in metadata for reference
            fake_message.raw_text += f" [REAL_ID: {real_msg['real_message_id']}]"
            
            fake_messages.append(fake_message)
            logger.info(f"   ✅ Created fake message {i}: '{real_msg['raw_text'][:50]}...' (Real ID: {real_msg['real_message_id']})")
            
        except Exception as e:
            logger.error(f"   ❌ Error creating fake message {i}: {e}")
            continue
    
    return fake_messages


def classify_messages(messages: List[WhatsAppMessage], session) -> Dict[int, str]:
    """Classify all messages using the classifier and database operations."""
    
    logger.info(f"🤖 Classifying {len(messages)} messages...")
    
    # Initialize the classifier
    classifier = MessageClassifier()
    logger.info("✅ Initialized MessageClassifier")
    
    # Prepare message data for classification
    message_data = []
    real_message_ids = {}
    
    for msg in messages:
        # Extract real message ID from message text if present
        real_message_id = None
        clean_text = msg.raw_text
        
        if "[REAL_ID:" in msg.raw_text:
            # Extract real message ID and clean the text
            import re
            match = re.search(r'\[REAL_ID: (\d+)\]', msg.raw_text)
            if match:
                real_message_id = int(match.group(1))
                clean_text = re.sub(r'\[REAL_ID: \d+\]', '', msg.raw_text).strip()
        
        message_data.append({'id': msg.id, 'raw_text': clean_text})
        real_message_ids[msg.id] = real_message_id
    
    # Classify messages with session for database-aware validation
    classification_results = classifier.classify_messages(message_data, session)
    
    # Process results using centralized classification logic
    processed_count = classifier.process_classification_results(classification_results, session)
    logger.info(f"✅ Processed {processed_count} messages using centralized classification logic")
    
    logger.info(f"✅ Completed classification of {len(messages)} messages")
    
    return real_message_ids


def print_comprehensive_summary(session, real_message_ids: Dict[int, str]) -> None:
    """Print a comprehensive summary of the classification results."""
    
    logger.info("="*80)
    logger.info("📊 COMPREHENSIVE CLASSIFICATION SUMMARY (REAL MESSAGES)")
    logger.info("="*80)
    
    # Get processing summary
    processing_summary = get_processing_summary(session)
    logger.info(f"📈 PROCESSING STATISTICS:")
    logger.info(f"   • Total Messages: {processing_summary['total_messages']}")
    logger.info(f"   • Processed Messages: {processing_summary['processed_messages']}")
    logger.info(f"   • Unprocessed Messages: {processing_summary['unprocessed_messages']}")
    logger.info(f"   • Processing Rate: {processing_summary['processing_rate']:.1f}%")
    logger.info(f"   • Total Classifications: {processing_summary['total_classifications']}")
    logger.info(f"   • Successful Classifications: {processing_summary['successful_classifications']}")
    logger.info(f"   • Success Rate: {processing_summary['success_rate']:.1f}%")
    
    # Get lead statistics
    lead_stats = get_lead_statistics(session)
    logger.info(f"🎯 LEAD STATISTICS:")
    logger.info(f"   • Total Leads Detected: {lead_stats['total_leads']}")
    logger.info(f"   • Recent Leads (24h): {lead_stats['recent_leads']}")
    
    if lead_stats['lead_categories']:
        logger.info(f"📂 LEAD CATEGORIES BREAKDOWN:")
        for category_name, lead_count in lead_stats['lead_categories']:
            logger.info(f"   • {category_name}: {lead_count} leads")
    
    if lead_stats['intent_types']:
        logger.info(f"🏷️  INTENT TYPES BREAKDOWN:")
        for intent_name, classification_count in lead_stats['intent_types']:
            logger.info(f"   • {intent_name}: {classification_count} classifications")
    
    # Get detailed lead summary
    detailed_leads = get_detailed_lead_summary(session)
    if detailed_leads:
        logger.info(f"📋 DETAILED LEAD BREAKDOWN:")
        for i, lead in enumerate(detailed_leads, 1):
            # Get the original message to find real message ID
            message = session.query(WhatsAppMessage).filter_by(id=lead['message_id']).first()
            real_message_id = real_message_ids.get(message.id) if message else None
            
            logger.info(f"\n   {i}. Lead ID: {lead['lead_id']}")
            logger.info(f"      Category: {lead['category_name']}")
            logger.info(f"      Real Message ID: {real_message_id or 'Unknown'}")
            logger.info(f"      Description: {lead['lead_for']}")
            logger.info(f"      Confidence: {lead['confidence_score']:.2f}")
            logger.info(f"      Sender: {lead['sender_name']}")
            logger.info(f"      Group: {lead['group_name']}")
            logger.info(f"      Message: '{lead['raw_text'][:100]}...'")
            logger.info(f"      Created: {lead['lead_created_at']}")
    
    logger.info(f"\n" + "="*80)
    logger.info("✅ SUMMARY COMPLETE")
    logger.info("="*80)


def main():
    """Main function to run the script."""
    
    logger.info("🤖 Real Message Classification Test Script")
    logger.info("=" * 60)
    
    if USE_REAL_DATABASE:
        logger.info("📝 Reading from REAL database, writing to REAL database!")
    else:
        logger.info("📝 Reading from REAL database, writing to FAKE database!")
    logger.info("=" * 60)
    
    # Read real unclassified messages
    real_messages = read_real_unclassified_messages(db_read_limit=50, result_limit=10)
    
    if not real_messages:
        logger.warning("⚠️  No unclassified messages found in production database")
        return
    
    if USE_REAL_DATABASE:
        # Use real database session
        with get_db_session() as session:
            # Create fake messages from real data in real database
            fake_messages = create_fake_messages_from_real_data(real_messages, session)
            logger.info(f"✅ Created {len(fake_messages)} fake messages from real data in real database")
            
            # Classify all messages
            real_message_ids = classify_messages(fake_messages, session)
            
            # Print comprehensive summary
            print_comprehensive_summary(session, real_message_ids)
    else:
        # Set up test database
        test_db = TestDatabase()
        test_db.setup()
        
        try:
            with test_db.get_session() as session:
                # Create fake messages from real data
                fake_messages = create_fake_messages_from_real_data(real_messages, session)
                logger.info(f"✅ Created {len(fake_messages)} fake messages from real data")
                
                # Classify all messages
                real_message_ids = classify_messages(fake_messages, session)
                
                # Print comprehensive summary
                print_comprehensive_summary(session, real_message_ids)
        
        finally:
            # Clean up test database
            test_db.teardown()
            logger.info("🧹 Test database cleaned up")


if __name__ == "__main__":
    main() 