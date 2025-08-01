#!/usr/bin/env python3
"""
Script to classify fake messages and add them to the test database.

This script is for manual testing and debugging purposes.
It takes multiple fake messages, classifies them using the real classifier,
and adds them to a clean test database, then provides a comprehensive summary.

Usage:
    python src/scripts/classify_fake_message.py
"""

import sys
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List

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
from src.utils.log import get_logger, setup_logger
from src.paths import logs_root

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


def create_all_sample_messages(session) -> List[WhatsAppMessage]:
    """Create all sample messages in the database."""
    
    # Sample messages to test
    sample_messages = [
        "Hi everyone! I'm looking for a good dentist in the area. Any recommendations?",
        "Need a plumber urgently, any recommendations?",
        "Can anyone recommend a good restaurant for dinner tonight?",
        "Hi everyone! How are you all doing today?",
        "Just checking in to see how everyone is doing!",
        "Looking for a reliable electrician for some home repairs",
        "Anyone know a good hair salon in the neighborhood?",
        "Need a tutor for my kids' math homework",
        "Great weather today! Hope everyone is having a good day",
        "Does anyone have recommendations for a good mechanic?"
    ]
    
    messages = []
    for i, message_text in enumerate(sample_messages, 1):
        message_id = create_fake_message_with_dependencies(session, message_text, user_id=i, group_id=1)
        message = session.query(WhatsAppMessage).filter_by(id=message_id).first()
        messages.append(message)
        logger.info(f"✅ Created message {i}: '{message_text[:50]}...'")
    
    return messages


def classify_messages(messages: List[WhatsAppMessage], session) -> None:
    """Classify all messages using the classifier and database operations."""
    
    logger.info(f"🤖 Classifying {len(messages)} messages...")
    
    # Initialize the classifier
    classifier = MessageClassifier()
    logger.info("✅ Initialized MessageClassifier")
    
    # Prepare message data for classification
    message_data = [
        {'id': msg.id, 'raw_text': msg.raw_text} 
        for msg in messages
    ]
    
    # Classify messages with session for database-aware validation
    classification_results = classifier.classify_messages(message_data, session)
    
    # Process results and update database
    for result in classification_results:
        if not result['success']:
            logger.error(f"❌ Failed to classify message {result['message_id']}: {result.get('error', 'Unknown error')}")
            continue
            
        message_id = result['message_id']
        classification_result = result['classification_result']
        
        try:
            # Get or create intent type
            intent_name = "lead_seeking" if classification_result.is_lead else "general_message"
            intent_type_id = get_or_create_intent_type(session, intent_name)
            
            # Get classification prompt
            prompt_template_id = get_classification_prompt(session)
            
            # Handle lead category
            if classification_result.is_lead and classification_result.lead_category:
                # Try to match with existing categories first
                matched_category = match_with_existing_categories(session, classification_result.lead_category)
                
                if matched_category:
                    # Use the matched existing category
                    lead_category_id = get_or_create_lead_category(session, matched_category)
                    logger.info(f"✅ Matched message to existing category: {matched_category}")
                else:
                    # Create new category
                    lead_category_id = get_or_create_lead_category(session, classification_result.lead_category)
                    logger.info(f"✅ Created new category: {classification_result.lead_category}")
            else:
                # For non-lead messages, use a general category
                lead_category_id = get_or_create_lead_category(session, "general")
            
            # Create classification record
            classification_id = create_classification_record(
                session=session,
                message_id=message_id,
                prompt_template_id=prompt_template_id,
                parsed_type_id=intent_type_id,
                lead_category_id=lead_category_id,
                confidence_score=classification_result.confidence_score,
                raw_llm_output=classification_result.model_dump()
            )
            
            # Create lead record if it's a lead
            if classification_result.is_lead:
                message = session.query(WhatsAppMessage).filter_by(id=message_id).first()
                lead_id = create_lead_record(
                    session=session,
                    classification_id=classification_id,
                    user_id=message.sender_id,
                    group_id=message.group_id,
                    lead_for=classification_result.lead_description or "Lead detected"
                )
                logger.info(f"   ✅ Created lead record (ID: {lead_id})")
            
            # Mark message as processed
            mark_message_as_processed(session, message_id)
            
            logger.info(f"   ✅ Successfully processed message {message_id}")
            
        except Exception as e:
            logger.error(f"   ❌ Error processing message {message_id}: {e}")
            continue
    
    logger.info(f"✅ Completed classification of {len(messages)} messages")


def print_comprehensive_summary(session) -> None:
    """Print a comprehensive summary of the classification results."""
    
    logger.info("="*80)
    logger.info("📊 COMPREHENSIVE CLASSIFICATION SUMMARY")
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
            logger.info(f"\n   {i}. Lead ID: {lead['lead_id']}")
            logger.info(f"      Category: {lead['category_name']}")
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
    
    logger.info("🤖 Fake Message Classification Script (Test Database)")
    logger.info("=" * 60)
    logger.info("📝 Using clean test database - no real data affected!")
    logger.info("=" * 60)
    
    # Set up test database
    test_db = TestDatabase()
    test_db.setup()
    
    try:
        with test_db.get_session() as session:
            # Create all sample messages
            logger.info("📝 Creating sample messages...")
            messages = create_all_sample_messages(session)
            logger.info(f"✅ Created {len(messages)} sample messages")
            
            # Classify all messages
            classify_messages(messages, session)
            
            # Print comprehensive summary
            print_comprehensive_summary(session)
    
    finally:
        # Clean up test database
        test_db.teardown()
        logger.info("🧹 Test database cleaned up")


if __name__ == "__main__":
    main() 