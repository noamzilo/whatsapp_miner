#!/usr/bin/env python3
"""
Test Database Isolation

This test verifies that we're using the test database, not the real database.
"""

import pytest
from unittest.mock import Mock, patch


class TestDatabaseIsolation:
    """Test that database isolation works correctly."""

    def test_database_isolation(self, classifier_with_test_db, test_data_factory):
        """Test that we're using the test database, not the real database."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Verify we're using the test database
        print(f"🔍 Test database engine: {test_db.engine}")
        print(f"🔍 Test database URL: {test_db.engine.url}")
        
        # Check if it's an in-memory database
        assert "memory" in str(test_db.engine.url), "Should be using in-memory database"
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Test message for isolation",
            llm_processed=False
        )
        
        # Verify the message was created in the test database
        from src.db.models.whatsapp_message import WhatsAppMessage
        messages = test_db.session.query(WhatsAppMessage).all()
        print(f"🔍 Number of messages in test database: {len(messages)}")
        
        # Should only have our test message
        assert len(messages) == 1, f"Expected 1 message, found {len(messages)}"
        assert messages[0].raw_text == "Test message for isolation"
        
        print("✅ Database isolation verified")

    def test_classifier_uses_test_database(self, classifier_with_test_db, test_data_factory):
        """Test that the classifier uses the test database."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Test message for classifier",
            llm_processed=False
        )

        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": true,
            "lead_category": "test",
            "lead_description": "Test lead",
            "confidence_score": 0.9,
            "reasoning": "Test reasoning"
        }'''
        mock_llm.invoke.return_value = mock_response

        # Get unclassified messages using the classifier
        unclassified = classifier._get_unclassified_messages(test_db.session)
        print(f"🔍 Unclassified messages found: {len(unclassified)}")
        
        # Should only find our test message
        assert len(unclassified) == 1, f"Expected 1 unclassified message, found {len(unclassified)}"
        assert unclassified[0].raw_text == "Test message for classifier"
        
        print("✅ Classifier uses test database correctly")

    def test_no_real_database_connection(self, classifier_with_test_db):
        """Test that we're not connecting to the real database."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Check that we're not using the real database URL
        real_db_url = "postgresql"  # Real database would be PostgreSQL
        test_db_url = str(test_db.engine.url)
        
        print(f"🔍 Test database URL: {test_db_url}")
        
        # Should not contain PostgreSQL (real database)
        assert "postgresql" not in test_db_url.lower(), "Should not be using PostgreSQL (real database)"
        
        # Should be SQLite in-memory
        assert "sqlite" in test_db_url.lower(), "Should be using SQLite"
        assert "memory" in test_db_url.lower(), "Should be using in-memory database"
        
        print("✅ No real database connection detected") 