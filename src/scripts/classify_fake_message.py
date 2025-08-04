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
from typing import Optional, List, Dict, Any

import re

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
    create_fake_message_with_dependencies, get_message_by_id
)
from src.utils.log import get_logger, setup_logger
from src.paths import logs_root

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


def create_all_sample_messages(session) -> List[WhatsAppMessage]:
    """Create all sample messages in the database."""
    
    # Sample messages with expected categories
    sample_messages_with_expected = [
        # Original test messages
        ("Hi everyone! I'm looking for a good dentist in the area. Any recommendations?", "dentist"),
        ("Need a plumber urgently, any recommendations?", "plumber"),
        ("Can anyone recommend a good restaurant for dinner tonight?", "restaurant"),
        ("Hi everyone! How are you all doing today?", None),  # Not a lead
        ("Just checking in to see how everyone is doing!", None),  # Not a lead
        ("Looking for a reliable electrician for some home repairs", "electrician"),
        ("Anyone know a good hair salon in the neighborhood?", "hair_salon"),
        ("Need a tutor for my kids' math homework", "math_tutor"),
        ("Great weather today! Hope everyone is having a good day", None),  # Not a lead
        ("Does anyone have recommendations for a good mechanic?", "mechanic"),
        
        # Additional messages with same categories (to test consistency)
        ("Looking for a dentist who takes my insurance", "dentist"),
        ("Need a plumber for a leaky faucet", "plumber"),
        ("Best restaurant for a date night?", "restaurant"),
        ("Electrician needed for new outlet installation", "electrician"),
        ("Recommendations for hair salon that does highlights?", "hair_salon"),
        ("Math tutor for high school algebra", "math_tutor"),
        ("Car mechanic for oil change and inspection", "mechanic"),
        
        # New categories to test
        ("Looking for a yoga instructor", "yoga_instructor"),
        ("Need a house cleaner for weekly cleaning", "house_cleaner"),
        ("Photographer for family portraits", "photographer"),
        ("Lawyer for traffic ticket", "lawyer"),
        ("Accountant for tax preparation", "accountant"),
        ("Real estate agent to sell my house", "real_estate_agent"),
        ("Pet groomer for my dog", "pet_groomer"),
        ("Landscaper for garden design", "landscaper"),
        ("Gym with personal trainer", "gym"),
        ("Spanish classes for beginners", "spanish_classes")
    ]
    
    messages = []
    for i, (message_text, expected_category) in enumerate(sample_messages_with_expected, 1):
        message_id = create_fake_message_with_dependencies(session, message_text, user_id=i, group_id=1)
        message = get_message_by_id(session, message_id)
        
        # Store expected category in message metadata (we'll use the description field temporarily)
        if expected_category:
            message.raw_text += f" [EXPECTED: {expected_category}]"
        
        messages.append(message)
        logger.info(f"✅ Created message {i}: '{message_text[:50]}...' (Expected: {expected_category})")
    
    return messages
    
    messages = []
    for i, message_text in enumerate(sample_messages, 1):
        message_id = create_fake_message_with_dependencies(session, message_text, user_id=i, group_id=1)
        message = get_message_by_id(session, message_id)
        messages.append(message)
        logger.info(f"✅ Created message {i}: '{message_text[:50]}...'")
    
    return messages


def classify_messages(messages: List[WhatsAppMessage], session) -> Dict[int, str]:
    """Classify all messages using the classifier and database operations."""
    
    logger.info(f"🤖 Classifying {len(messages)} messages...")
    
    # Initialize the classifier
    classifier = MessageClassifier()
    logger.info("✅ Initialized MessageClassifier")
    
    # Prepare message data for classification
    message_data = []
    expected_categories = {}
    
    for msg in messages:
        # Extract expected category from message text if present
        expected_category = None
        clean_text = msg.raw_text
        
        if "[EXPECTED:" in msg.raw_text:
            # Extract expected category and clean the text
            match = re.search(r'\[EXPECTED: (\w+)\]', msg.raw_text)
            if match:
                expected_category = match.group(1)
                clean_text = re.sub(r'\[EXPECTED: \w+\]', '', msg.raw_text).strip()
        
        message_data.append({'id': msg.id, 'raw_text': clean_text})
        expected_categories[msg.id] = expected_category
    
    # Classify messages with session for database-aware validation
    classification_results = classifier.classify_messages(message_data, session)
    
    # Process results and update database using centralized logic
    processed_count = classifier.process_classification_results(classification_results, session)
    logger.info(f"✅ Processed {processed_count} messages using centralized classification logic")
    
    logger.info(f"✅ Completed classification of {len(messages)} messages")
    
    return expected_categories


def print_comprehensive_summary(session, expected_categories: Dict[int, str]) -> None:
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
            # Get the original message to find expected category
            message = get_message_by_id(session, lead['message_id'])
            expected_category = expected_categories.get(message.id) if message else None
            
            logger.info(f"\n   {i}. Lead ID: {lead['lead_id']}")
            logger.info(f"      Category: {lead['category_name']}")
            logger.info(f"      Expected: {expected_category or 'None'}")
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
            expected_categories = classify_messages(messages, session)
            
            # Print comprehensive summary
            print_comprehensive_summary(session, expected_categories)
    
    finally:
        # Clean up test database
        test_db.teardown()
        logger.info("🧹 Test database cleaned up")


if __name__ == "__main__":
    main() 