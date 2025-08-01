#!/usr/bin/env python3
"""
Test Database Setup

Provides test database functionality with proper migrations and test data.
"""

import pytest
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Dict, Any

from src.db.models import Base
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_classification_prompt import LeadClassificationPrompt
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType


class TestDatabase:
    """Test database with proper setup and teardown."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.session = None
    
    def setup(self):
        """Set up test database with migrations."""
        # Create in-memory SQLite database with unique name to avoid conflicts
        import uuid
        db_name = f"test_db_{uuid.uuid4().hex[:8]}"
        self.engine = create_engine(
            f"sqlite:///:memory:{db_name}",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        
        # Create all tables (this runs migrations)
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = self.SessionLocal()
        
        # Set up default test data
        self._setup_default_data()
    
    def teardown(self):
        """Clean up test database."""
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()
    
    def _setup_default_data(self):
        """Set up default test data."""
        # Create default classification prompt
        default_prompt = LeadClassificationPrompt(
            template_name="lead_classification",
            prompt_text="""You are a classifier for WhatsApp messages from local groups. Your task is to determine if a message represents someone looking for a local service.

Services can include: dentist, spanish classes, restaurants, tutors, plumbers, electricians, and any other local business or service.

Analyze the message and respond with a JSON object containing:
- is_lead: boolean indicating if this is a lead
- lead_category: string describing the category (if it's a lead)
- lead_description: string describing what they're looking for (if it's a lead)
- confidence_score: float between 0 and 1
- reasoning: string explaining your classification

Message: {message_text}""",
            version="1.0"
        )
        self.session.add(default_prompt)
        self.session.commit()
    
    @contextmanager
    def get_session(self) -> Generator:
        """Get a database session."""
        try:
            yield self.session
        except Exception:
            self.session.rollback()
            raise
        finally:
            self.session.commit()


class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_test_user(session, user_id: int = 1, **kwargs) -> WhatsAppUser:
        """Create a test user."""
        user = WhatsAppUser(
            id=user_id,
            whatsapp_id=kwargs.get('whatsapp_id', f"user{user_id}"),
            display_name=kwargs.get('display_name', f"Test User {user_id}"),
            created_at=kwargs.get('created_at', datetime.now(timezone.utc))
        )
        session.add(user)
        session.commit()
        return user
    
    @staticmethod
    def create_test_group(session, group_id: int = 1, **kwargs) -> WhatsAppGroup:
        """Create a test group."""
        group = WhatsAppGroup(
            id=group_id,
            whatsapp_group_id=kwargs.get('whatsapp_group_id', f"group{group_id}"),
            group_name=kwargs.get('group_name', f"Test Group {group_id}"),
            location_city=kwargs.get('location_city', "Test City"),
            location_neighbourhood=kwargs.get('location_neighbourhood', "Test Neighbourhood"),
            location=kwargs.get('location', "Test Location"),
            created_at=kwargs.get('created_at', datetime.now(timezone.utc))
        )
        session.add(group)
        session.commit()
        return group
    
    @staticmethod
    def create_test_message(session, message_id: int = None, **kwargs) -> WhatsAppMessage:
        """Create a test message."""
        # Generate unique ID if not provided
        if message_id is None:
            import uuid
            message_id = int(uuid.uuid4().hex[:8], 16) % 1000000  # Use last 6 digits of UUID
        
        message = WhatsAppMessage(
            id=message_id,
            message_id=kwargs.get('message_id', f"msg{message_id}"),
            sender_id=kwargs.get('sender_id', 1),
            group_id=kwargs.get('group_id', 1),
            timestamp=kwargs.get('timestamp', datetime.now(timezone.utc)),
            raw_text=kwargs.get('raw_text', "Test message"),
            message_type=kwargs.get('message_type', "text"),
            is_forwarded=kwargs.get('is_forwarded', False),
            llm_processed=kwargs.get('llm_processed', False)
        )
        session.add(message)
        session.commit()
        return message
    
    @staticmethod
    def create_test_lead_category(session, category_id: int = 1, **kwargs) -> LeadCategory:
        """Create a test lead category."""
        category = LeadCategory(
            id=category_id,
            name=kwargs.get('name', f"test_category_{category_id}"),
            description=kwargs.get('description', f"Test category {category_id}"),
            opening_message_template=kwargs.get('opening_message_template', f"Hi! I saw you're looking for {kwargs.get('name', f'test_category_{category_id}')} services. How can I help?")
        )
        session.add(category)
        session.commit()
        return category
    
    @staticmethod
    def create_test_intent_type(session, intent_id: int = 1, **kwargs) -> MessageIntentType:
        """Create a test intent type."""
        intent = MessageIntentType(
            id=intent_id,
            name=kwargs.get('name', f"test_intent_{intent_id}"),
            description=kwargs.get('description', f"Test intent {intent_id}")
        )
        session.add(intent)
        session.commit()
        return intent


# Sample test messages for different scenarios
SAMPLE_MESSAGES = {
    "lead_dentist": {
        "raw_text": "Hi everyone! I'm looking for a good dentist in the area. Any recommendations?",
        "expected_lead": True,
        "expected_category": "dentist",
        "expected_description": "Looking for a dentist"
    },
    "lead_plumber": {
        "raw_text": "Need a plumber urgently, any recommendations?",
        "expected_lead": True,
        "expected_category": "plumber",
        "expected_description": "Looking for a plumber"
    },
    "lead_restaurant": {
        "raw_text": "Can anyone recommend a good restaurant for dinner tonight?",
        "expected_lead": True,
        "expected_category": "restaurant",
        "expected_description": "Looking for a restaurant"
    },
    "non_lead_greeting": {
        "raw_text": "Hi everyone! How are you all doing today?",
        "expected_lead": False,
        "expected_category": None,
        "expected_description": None
    },
    "non_lead_general": {
        "raw_text": "Just checking in to see how everyone is doing!",
        "expected_lead": False,
        "expected_category": None,
        "expected_description": None
    }
} 