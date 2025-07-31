#!/usr/bin/env python3
"""
Integration Tests for MessageClassifier

Tests that use a real in-memory SQLite database to test the full end-to-end flow.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.message_classification.message_classifier import MessageClassifier, ClassificationResult
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_classification_prompt import LeadClassificationPrompt
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType


class TestMessageClassifierIntegration:
    """Integration tests using real in-memory database."""

    @pytest.fixture
    def test_db_engine(self):
        """Create an in-memory SQLite database for testing."""
        # Create in-memory SQLite database
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        
        # Import and create all tables
        from src.db.models.base import Base
        Base.metadata.create_all(engine)
        
        return engine

    @pytest.fixture
    def test_db_session(self, test_db_engine):
        """Create a database session for testing."""
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        session = SessionLocal()
        
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM responses for testing."""
        return {
            "lead_message": {
                "is_lead": True,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message clearly asks for dentist recommendations"
            },
            "non_lead_message": {
                "is_lead": False,
                "lead_category": None,
                "lead_description": None,
                "confidence_score": 0.8,
                "reasoning": "This is just a general conversation message"
            }
        }

    @pytest.fixture
    def setup_test_data(self, test_db_session):
        """Set up test data in the database."""
        # Create test prompt
        prompt = LeadClassificationPrompt(
            template_name="lead_classification",
            prompt_text="Test prompt for classification",
            version="1.0"
        )
        test_db_session.add(prompt)
        test_db_session.commit()
        
        # Create test intent types
        lead_intent = MessageIntentType(
            name="lead_seeking",
            description="Intent for lead seeking messages"
        )
        general_intent = MessageIntentType(
            name="general_message",
            description="Intent for general messages"
        )
        test_db_session.add(lead_intent)
        test_db_session.add(general_intent)
        test_db_session.commit()
        
        # Create test lead categories
        dentist_category = LeadCategory(
            name="dentist",
            description="Dentist services",
            opening_message_template="Hi! I saw you're looking for dentist services. How can I help?"
        )
        test_db_session.add(dentist_category)
        test_db_session.commit()
        
        return {
            "prompt": prompt,
            "lead_intent": lead_intent,
            "general_intent": general_intent,
            "dentist_category": dentist_category
        }

    def test_end_to_end_lead_classification(self, test_db_session, setup_test_data, mock_llm_response):
        """Test the complete end-to-end flow for lead classification."""
        # Mock the LLM to return a lead response
        with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = str(mock_llm_response["lead_message"]).replace("'", '"')
            mock_llm.invoke.return_value = mock_response
            mock_chat_groq.return_value = mock_llm
            
            # Create a test message
            test_message = WhatsAppMessage(
                id="test_msg_1",
                sender_id="user123",
                group_id="group456",
                raw_text="Hi everyone! I'm looking for a good dentist in the area. Any recommendations?",
                timestamp="2024-01-01T10:00:00Z",
                llm_processed=False
            )
            test_db_session.add(test_message)
            test_db_session.commit()
            
            # Initialize classifier with mocked dependencies
            with patch('src.message_classification.message_classifier.groq_api_key', 'test_key'):
                with patch('src.message_classification.message_classifier.message_classifier_run_every_seconds', 30):
                    with patch('src.message_classification.message_classifier.get_db_session') as mock_get_db:
                        mock_get_db.return_value.__enter__.return_value = test_db_session
                        mock_get_db.return_value.__exit__.return_value = None
                        
                        classifier = MessageClassifier()
                        
                        # Run classification
                        classifier.classify_messages()
                        
                        # Verify the message was marked as processed
                        test_db_session.refresh(test_message)
                        assert test_message.llm_processed is True
                        
                        # Verify classification record was created
                        classification = test_db_session.query(MessageIntentClassification).filter_by(
                            message_id="test_msg_1"
                        ).first()
                        assert classification is not None
                        assert classification.confidence_score == 0.9
                        
                        # Verify lead record was created
                        lead = test_db_session.query(DetectedLead).filter_by(
                            classification_id=classification.id
                        ).first()
                        assert lead is not None
                        assert lead.user_id == "user123"
                        assert lead.group_id == "group456"
                        assert lead.lead_for == "Looking for a dentist"

    def test_end_to_end_non_lead_classification(self, test_db_session, setup_test_data, mock_llm_response):
        """Test the complete end-to-end flow for non-lead classification."""
        # Mock the LLM to return a non-lead response
        with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = str(mock_llm_response["non_lead_message"]).replace("'", '"')
            mock_llm.invoke.return_value = mock_response
            mock_chat_groq.return_value = mock_llm
            
            # Create a test message
            test_message = WhatsAppMessage(
                id="test_msg_2",
                sender_id="user456",
                group_id="group789",
                raw_text="Just checking in to see how everyone is doing today!",
                timestamp="2024-01-01T11:00:00Z",
                llm_processed=False
            )
            test_db_session.add(test_message)
            test_db_session.commit()
            
            # Initialize classifier with mocked dependencies
            with patch('src.message_classification.message_classifier.groq_api_key', 'test_key'):
                with patch('src.message_classification.message_classifier.message_classifier_run_every_seconds', 30):
                    with patch('src.message_classification.message_classifier.get_db_session') as mock_get_db:
                        mock_get_db.return_value.__enter__.return_value = test_db_session
                        mock_get_db.return_value.__exit__.return_value = None
                        
                        classifier = MessageClassifier()
                        
                        # Run classification
                        classifier.classify_messages()
                        
                        # Verify the message was marked as processed
                        test_db_session.refresh(test_message)
                        assert test_message.llm_processed is True
                        
                        # Verify classification record was created
                        classification = test_db_session.query(MessageIntentClassification).filter_by(
                            message_id="test_msg_2"
                        ).first()
                        assert classification is not None
                        assert classification.confidence_score == 0.8
                        assert classification.lead_category_id is None  # No lead category for non-lead
                        
                        # Verify NO lead record was created
                        lead = test_db_session.query(DetectedLead).filter_by(
                            classification_id=classification.id
                        ).first()
                        assert lead is None

    def test_database_operations_with_real_data(self, test_db_session, setup_test_data):
        """Test database operations with real data structures."""
        # Test creating a lead category
        plumber_category = LeadCategory(
            name="plumber",
            description="Plumbing services",
            opening_message_template="Hi! I saw you're looking for plumbing services. How can I help?"
        )
        test_db_session.add(plumber_category)
        test_db_session.commit()
        
        # Verify it was created
        retrieved_category = test_db_session.query(LeadCategory).filter_by(name="plumber").first()
        assert retrieved_category is not None
        assert retrieved_category.description == "Plumbing services"
        
        # Test creating a message intent classification
        classification = MessageIntentClassification(
            message_id="test_msg_3",
            prompt_template_id=setup_test_data["prompt"].id,
            intent_type_id=setup_test_data["lead_intent"].id,
            lead_category_id=plumber_category.id,
            confidence_score=0.85,
            raw_llm_output={"test": "data"}
        )
        test_db_session.add(classification)
        test_db_session.commit()
        
        # Verify it was created
        retrieved_classification = test_db_session.query(MessageIntentClassification).filter_by(
            message_id="test_msg_3"
        ).first()
        assert retrieved_classification is not None
        assert retrieved_classification.confidence_score == 0.85
        assert retrieved_classification.lead_category_id == plumber_category.id

    def test_multiple_messages_classification(self, test_db_session, setup_test_data, mock_llm_response):
        """Test classifying multiple messages in one run."""
        # Create multiple test messages
        messages = [
            WhatsAppMessage(
                id=f"test_msg_{i}",
                sender_id=f"user{i}",
                group_id="group123",
                raw_text=f"Test message {i}",
                timestamp=f"2024-01-01T{i:02d}:00:00Z",
                llm_processed=False
            )
            for i in range(1, 4)
        ]
        
        for msg in messages:
            test_db_session.add(msg)
        test_db_session.commit()
        
        # Mock LLM to return lead response for all messages
        with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = str(mock_llm_response["lead_message"]).replace("'", '"')
            mock_llm.invoke.return_value = mock_response
            mock_chat_groq.return_value = mock_llm
            
            # Initialize classifier
            with patch('src.message_classification.message_classifier.groq_api_key', 'test_key'):
                with patch('src.message_classification.message_classifier.message_classifier_run_every_seconds', 30):
                    with patch('src.message_classification.message_classifier.get_db_session') as mock_get_db:
                        mock_get_db.return_value.__enter__.return_value = test_db_session
                        mock_get_db.return_value.__exit__.return_value = None
                        
                        classifier = MessageClassifier()
                        
                        # Run classification
                        classifier.classify_messages()
                        
                        # Verify all messages were processed
                        for msg in messages:
                            test_db_session.refresh(msg)
                            assert msg.llm_processed is True
                        
                        # Verify classifications were created
                        classifications = test_db_session.query(MessageIntentClassification).all()
                        assert len(classifications) == 3
                        
                        # Verify leads were created
                        leads = test_db_session.query(DetectedLead).all()
                        assert len(leads) == 3 