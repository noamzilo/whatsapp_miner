#!/usr/bin/env python3
"""
Test Database Setup

Provides test database functionality with proper migrations and test data.
Uses the same API as the main database to ensure consistency.
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

from src.db.db_interface import DbInterface
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_classification_prompt import LeadClassificationPrompt
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType
from src.db.db import (
    create_or_get_user, create_or_get_group, create_message_with_dependencies,
    get_or_create_lead_category, get_or_create_intent_type, get_classification_prompt
)


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
        DbInterface.metadata.create_all(self.engine)
        
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
        """Set up default test data using the main database API."""
        # Create default classification prompt using the main API
        get_classification_prompt(self.session)
    
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
    """Factory for creating test data using the main database API."""
    
    @staticmethod
    def create_test_user(session, user_id: int = 1, **kwargs) -> WhatsAppUser:
        """Create a test user using the main database API."""
        whatsapp_id = kwargs.get('whatsapp_id', f"user{user_id}@c.us")
        display_name = kwargs.get('display_name', f"Test User {user_id}")
        
        # Use the main database API
        user_id = create_or_get_user(session, whatsapp_id, display_name)
        return session.query(WhatsAppUser).filter_by(id=user_id).first()
    
    @staticmethod
    def create_test_group(session, group_id: int = 1, **kwargs) -> WhatsAppGroup:
        """Create a test group using the main database API."""
        whatsapp_group_id = kwargs.get('whatsapp_group_id', f"group{group_id}@g.us")
        group_name = kwargs.get('group_name', f"Test Group {group_id}")
        
        # Use the main database API
        group_id = create_or_get_group(session, whatsapp_group_id, group_name)
        return session.query(WhatsAppGroup).filter_by(id=group_id).first()
    
    @staticmethod
    def create_test_message(session, message_id: str = None, **kwargs) -> WhatsAppMessage:
        """Create a test message using the main database API."""
        # Generate unique message ID if not provided
        if message_id is None:
            import uuid
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            message_id = f"test_msg_{timestamp}_{unique_id}"
        
        # Use the main database API for atomic operation
        message_id = create_message_with_dependencies(
            session=session,
            message_id=message_id,
            whatsapp_user_id=kwargs.get('whatsapp_user_id', "user1@c.us"),
            whatsapp_group_id=kwargs.get('whatsapp_group_id', "group1@g.us"),
            raw_text=kwargs.get('raw_text', "Test message"),
            user_display_name=kwargs.get('user_display_name', "Test User 1"),
            group_name=kwargs.get('group_name', "Test Group 1"),
            message_type=kwargs.get('message_type', "text"),
            is_forwarded=kwargs.get('is_forwarded', False)
        )
        
        return session.query(WhatsAppMessage).filter_by(id=message_id).first()
    
    @staticmethod
    def create_test_lead_category(session, category_id: int = 1, **kwargs) -> LeadCategory:
        """Create a test lead category using the main database API."""
        category_name = kwargs.get('name', f"test_category_{category_id}")
        
        # Use the main database API
        category_id = get_or_create_lead_category(session, category_name)
        return session.query(LeadCategory).filter_by(id=category_id).first()
    
    @staticmethod
    def create_test_intent_type(session, intent_id: int = 1, **kwargs) -> MessageIntentType:
        """Create a test intent type using the main database API."""
        intent_name = kwargs.get('name', f"test_intent_{intent_id}")
        
        # Use the main database API
        intent_id = get_or_create_intent_type(session, intent_name)
        return session.query(MessageIntentType).filter_by(id=intent_id).first()


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