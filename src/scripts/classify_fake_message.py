#!/usr/bin/env python3
"""
Script to classify a fake message and add it to the real database.

This script is for manual testing and debugging purposes.
It takes a fake message, classifies it using the real classifier,
and adds it to the real database.

Usage:
    python src/scripts/classify_fake_message.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from src.message_classification.message_classifier import MessageClassifier
from src.db.db import get_db_session
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType


def create_fake_message(
    session,
    message_text: str,
    user_id: int = 1,
    group_id: int = 1,
    message_id: str = "fake_msg_001"
) -> WhatsAppMessage:
    """Create a fake message in the database."""
    
    # Create fake user if it doesn't exist
    user = session.query(WhatsAppUser).filter_by(id=user_id).first()
    if not user:
        user = WhatsAppUser(
            id=user_id,
            whatsapp_id=f"fake_user_{user_id}",
            display_name=f"Fake User {user_id}",
            created_at=datetime.now(timezone.utc)
        )
        session.add(user)
        session.commit()
    
    # Create fake group if it doesn't exist
    group = session.query(WhatsAppGroup).filter_by(id=group_id).first()
    if not group:
        group = WhatsAppGroup(
            id=group_id,
            whatsapp_group_id=f"fake_group_{group_id}",
            group_name=f"Fake Group {group_id}",
            location_city="Fake City",
            location_neighbourhood="Fake Neighbourhood",
            location="Fake Location",
            created_at=datetime.now(timezone.utc)
        )
        session.add(group)
        session.commit()
    
    # Create the fake message
    message = WhatsAppMessage(
        message_id=message_id,
        sender_id=user_id,
        group_id=group_id,
        timestamp=datetime.now(timezone.utc),
        raw_text=message_text,
        message_type="text",
        is_forwarded=False,
        llm_processed=False
    )
    session.add(message)
    session.commit()
    
    return message


def classify_fake_message(message_text: str) -> None:
    """Classify a fake message and add it to the database."""
    
    print(f"🔍 Classifying fake message: '{message_text}'")
    
    with get_db_session() as session:
        # Create the fake message
        message = create_fake_message(session, message_text)
        print(f"✅ Created fake message with ID: {message.id}")
        
        # Initialize the classifier
        classifier = MessageClassifier()
        print("✅ Initialized MessageClassifier")
        
        # Classify the message
        print("🤖 Running classification...")
        classification_result = classifier._classify_message(message_text)
        
        print(f"📊 Classification result:")
        print(f"   - Is Lead: {classification_result.is_lead}")
        print(f"   - Lead Category: {classification_result.lead_category}")
        print(f"   - Lead Description: {classification_result.lead_description}")
        print(f"   - Confidence Score: {classification_result.confidence_score}")
        print(f"   - Reasoning: {classification_result.reasoning}")
        
        # Create classification record
        print("💾 Creating classification record...")
        classification = classifier._create_classification_record(
            session, message, classification_result
        )
        print(f"✅ Created classification record with ID: {classification.id}")
        
        # Create lead record if it's a lead
        if classification_result.is_lead:
            print("🎯 Creating lead record...")
            lead = classifier._create_lead_record(
                session, message, classification, classification_result
            )
            print(f"✅ Created lead record with ID: {lead.id}")
        else:
            print("ℹ️  No lead record created (not a lead)")
        
        # Mark message as processed
        print("✅ Marking message as processed...")
        classifier._mark_message_as_processed(session, message)
        
        print("🎉 Fake message classification completed successfully!")
        
        # Print summary
        print("\n📋 Summary:")
        print(f"   - Message ID: {message.id}")
        print(f"   - Classification ID: {classification.id}")
        if classification_result.is_lead:
            print(f"   - Lead ID: {lead.id}")
        print(f"   - Processed: {message.llm_processed}")


def main():
    """Main function to run the script."""
    
    # Sample messages to test
    sample_messages = [
        "Hi everyone! I'm looking for a good dentist in the area. Any recommendations?",
        "Need a plumber urgently, any recommendations?",
        "Can anyone recommend a good restaurant for dinner tonight?",
        "Hi everyone! How are you all doing today?",
        "Just checking in to see how everyone is doing!"
    ]
    
    print("🤖 Fake Message Classification Script")
    print("=" * 50)
    
    # Ask user which message to classify
    print("\nAvailable sample messages:")
    for i, msg in enumerate(sample_messages, 1):
        print(f"   {i}. {msg}")
    print("   6. Enter custom message")
    
    try:
        choice = input("\nSelect a message to classify (1-6): ").strip()
        
        if choice == "6":
            message_text = input("Enter your custom message: ").strip()
            if not message_text:
                print("❌ No message provided. Exiting.")
                return
        elif choice.isdigit() and 1 <= int(choice) <= 5:
            message_text = sample_messages[int(choice) - 1]
        else:
            print("❌ Invalid choice. Exiting.")
            return
        
        print(f"\n🎯 Selected message: '{message_text}'")
        
        # Confirm before proceeding
        confirm = input("\nProceed with classification? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Cancelled by user.")
            return
        
        # Run the classification
        classify_fake_message(message_text)
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 