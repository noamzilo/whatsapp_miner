#!/usr/bin/env python3
"""
Level 3: Database Integration Tests

Tests the database integration with test database and mock messages.
These tests verify that the database operations work correctly.
"""

import pytest
from datetime import datetime, timezone


class TestDatabaseIntegration:
    """Test database integration with test database."""
    
    def test_database_setup(self, test_db):
        """Test that the test database is set up correctly."""
        # Verify database is accessible
        assert test_db.session is not None
        assert test_db.engine is not None
        
        # Verify default data is created
        from src.db.models.lead_classification_prompt import LeadClassificationPrompt
        prompts = test_db.session.query(LeadClassificationPrompt).all()
        assert len(prompts) == 1
        assert prompts[0].template_name == "lead_classification"
    
    def test_database_migrations(self, test_db):
        """Test that database migrations are applied correctly."""
        # Verify all tables exist
        from src.db.models import Base
        from sqlalchemy import inspect
        
        inspector = inspect(test_db.engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'whatsapp_messages',
            'whatsapp_users', 
            'whatsapp_groups',
            'message_intent_classifications',
            'detected_leads',
            'lead_classification_prompts',
            'lead_categories',
            'message_intent_types'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
    
    def test_test_data_factory(self, test_session, test_data_factory):
        """Test that the test data factory works correctly."""
        # Create test user
        user = test_data_factory.create_test_user(test_session, user_id=1)
        assert user.id == 1
        assert user.whatsapp_id == "user1"
        assert user.display_name == "Test User 1"
        
        # Create test group
        group = test_data_factory.create_test_group(test_session, group_id=1)
        assert group.id == 1
        assert group.whatsapp_group_id == "group1"
        assert group.group_name == "Test Group 1"
        
        # Create test message
        message = test_data_factory.create_test_message(
            test_session, 
            message_id=1,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Test message"
        )
        assert message.id == 1
        assert message.sender_id == user.id
        assert message.group_id == group.id
        assert message.raw_text == "Test message"
        assert message.llm_processed is False
    
    def test_database_session_management(self, test_db):
        """Test that database session management works correctly."""
        with test_db.get_session() as session:
            # Test that we can query the database
            from src.db.models.lead_classification_prompt import LeadClassificationPrompt
            prompts = session.query(LeadClassificationPrompt).all()
            assert len(prompts) == 1
            
            # Test that we can add data
            from src.db.models.whatsapp_user import WhatsAppUser
            user = WhatsAppUser(
                whatsapp_id="test_user",
                display_name="Test User"
            )
            session.add(user)
            # Session should be committed automatically by context manager
    
    def test_classifier_with_test_database(self, classifier_with_test_db):
        """Test that the classifier works with the test database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Verify classifier can access the database
        unclassified = classifier._get_unclassified_messages(test_db.session)
        assert len(unclassified) == 0  # No messages initially
        
        # Verify prompt is available
        prompt = classifier._get_classification_prompt()
        assert prompt is not None
        assert "is_lead" in prompt
    
    def test_database_lead_category_creation(self, classifier_with_test_db):
        """Test lead category creation in database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create a lead category
        category = classifier._get_or_create_lead_category(test_db.session, "dentist")
        assert category.name == "dentist"
        assert category.description == "Category for dentist leads"
        
        # Verify it was saved to database
        from src.db.models.lead_category import LeadCategory
        saved_category = test_db.session.query(LeadCategory).filter_by(name="dentist").first()
        assert saved_category is not None
        assert saved_category.id == category.id
    
    def test_database_intent_type_creation(self, classifier_with_test_db):
        """Test intent type creation in database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create an intent type
        intent_type = classifier._get_or_create_intent_type(test_db.session, "lead_seeking")
        assert intent_type.name == "lead_seeking"
        assert intent_type.description == "Intent type for lead_seeking"
        
        # Verify it was saved to database
        from src.db.models.message_intent_type import MessageIntentType
        saved_intent = test_db.session.query(MessageIntentType).filter_by(name="lead_seeking").first()
        assert saved_intent is not None
        assert saved_intent.id == intent_type.id
    
    def test_database_message_processing(self, classifier_with_test_db, test_data_factory):
        """Test message processing in database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a dentist"
        )
        
        # Verify message is unprocessed initially
        assert message.llm_processed is False
        
        # Mark message as processed
        classifier._mark_message_as_processed(test_db.session, message)
        
        # Verify message is now processed
        assert message.llm_processed is True
        
        # Verify change was saved to database
        test_db.session.refresh(message)
        assert message.llm_processed is True
    
    def test_database_classification_record_creation(self, classifier_with_test_db, test_data_factory):
        """Test classification record creation in database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a dentist"
        )
        
        # Create classification result
        from src.message_classification.message_classifier import ClassificationResult
        classification_result = ClassificationResult(
            is_lead=True,
            lead_category="dentist",
            lead_description="Looking for a dentist",
            confidence_score=0.9,
            reasoning="Message asks for dentist recommendations"
        )
        
        # Create classification record
        classification = classifier._create_classification_record(
            test_db.session,
            message,
            classification_result
        )
        
        # Verify classification record was created
        assert classification.message_id == message.id
        assert classification.confidence_score == 0.9
        assert classification.raw_llm_output['is_lead'] is True
        assert classification.raw_llm_output['lead_category'] == "dentist"
        
        # Verify it was saved to database
        from src.db.models.message_intent_classification import MessageIntentClassification
        saved_classification = test_db.session.query(MessageIntentClassification).filter_by(
            message_id=message.id
        ).first()
        assert saved_classification is not None
        assert saved_classification.id == classification.id
    
    def test_database_lead_record_creation(self, classifier_with_test_db, test_data_factory):
        """Test lead record creation in database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a dentist"
        )
        
        # Create classification record first
        from src.message_classification.message_classifier import ClassificationResult
        classification_result = ClassificationResult(
            is_lead=True,
            lead_category="dentist",
            lead_description="Looking for a dentist",
            confidence_score=0.9,
            reasoning="Message asks for dentist recommendations"
        )
        
        classification = classifier._create_classification_record(
            test_db.session,
            message,
            classification_result
        )
        
        # Create lead record
        lead = classifier._create_lead_record(
            test_db.session,
            message,
            classification,
            classification_result
        )
        
        # Verify lead record was created
        assert lead.classification_id == classification.id
        assert lead.user_id == user.id
        assert lead.group_id == group.id
        assert lead.lead_for == "Looking for a dentist"
        
        # Verify it was saved to database
        from src.db.models.detected_lead import DetectedLead
        saved_lead = test_db.session.query(DetectedLead).filter_by(
            classification_id=classification.id
        ).first()
        assert saved_lead is not None
        assert saved_lead.id == lead.id
    
    def test_database_unclassified_messages_query(self, classifier_with_test_db, test_data_factory):
        """Test querying unclassified messages from database."""
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        
        # Create unprocessed message
        unprocessed_message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a dentist",
            llm_processed=False
        )
        
        # Create processed message
        processed_message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Already processed message",
            llm_processed=True
        )
        
        # Query unclassified messages
        unclassified = classifier._get_unclassified_messages(test_db.session)
        
        # Should only return unprocessed message
        assert len(unclassified) == 1
        assert unclassified[0].id == unprocessed_message.id
        assert unclassified[0].llm_processed is False 