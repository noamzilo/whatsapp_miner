#!/usr/bin/env python3
"""
Mock Database Tests

Tests that demonstrate how to use the mock database for testing database operations.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from src.message_classification.message_classifier import MessageClassifier, ClassificationResult


class TestMockDatabase:
    """Tests demonstrating mock database usage."""

    def test_mock_db_session_basic(self, mock_db_session):
        """Test basic mock database session operations."""
        # The mock_db_session fixture provides a mocked database session
        # that can be used to test database operations without a real database
        
        # Test that we can call database methods
        mock_db_session.query.assert_not_called()
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()
        
        # Simulate some database operations
        mock_db_session.add("some_object")
        mock_db_session.commit()
        
        # Verify the methods were called
        mock_db_session.add.assert_called_once_with("some_object")
        mock_db_session.commit.assert_called_once()

    def test_mock_db_with_data(self, mock_db_with_data):
        """Test mock database with pre-populated test data."""
        # This fixture provides a mock database with some test data already set up
        
        # Test querying for a prompt
        from src.db.models.lead_classification_prompt import LeadClassificationPrompt
        result = mock_db_with_data.query(LeadClassificationPrompt).filter().first()
        
        # Verify the mock returned the expected data
        assert result is not None
        assert result.template_name == "lead_classification"
        assert result.prompt_text == "Test classification prompt"
        
        # Test querying for an intent type
        from src.db.models.message_intent_type import MessageIntentType
        intent_result = mock_db_with_data.query(MessageIntentType).filter().first()
        
        assert intent_result is not None
        assert intent_result.name == "lead_seeking"

    def test_classifier_with_mock_db(self, mock_db_with_data):
        """Test MessageClassifier with mock database."""
        # Mock the LLM
        with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = '''{
                "is_lead": true,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message asks for dentist recommendations"
            }'''
            mock_llm.invoke.return_value = mock_response
            mock_chat_groq.return_value = mock_llm
            
            # Initialize classifier with mocked dependencies
            with patch('src.message_classification.message_classifier.groq_api_key', 'test_key'):
                with patch('src.message_classification.message_classifier.message_classifier_run_every_seconds', 30):
                    with patch('src.message_classification.message_classifier.get_db_session') as mock_get_db:
                        mock_get_db.return_value.__enter__.return_value = mock_db_with_data
                        mock_get_db.return_value.__exit__.return_value = None
                        
                        classifier = MessageClassifier()
                        
                        # Test that the classifier can be initialized
                        assert classifier.llm is not None
                        assert classifier.output_parser is not None
                        assert classifier.classification_prompt is not None
                        
                        # Test that database operations are called
                        # (The actual operations are mocked, but we can verify they're called)
                        mock_db_with_data.query.assert_called()

    def test_database_operation_tracking(self, mock_db_session):
        """Test that we can track database operations."""
        # Create a test object
        test_object = Mock()
        test_object.id = "test_id"
        test_object.name = "test_name"
        
        # Simulate database operations
        mock_db_session.add(test_object)
        mock_db_session.commit()
        
        # Verify operations were tracked
        mock_db_session.add.assert_called_once_with(test_object)
        mock_db_session.commit.assert_called_once()
        
        # Test query operations
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = test_object
        mock_db_session.query.return_value = mock_query
        
        # Simulate a query
        result = mock_db_session.query("SomeModel").filter().first()
        
        # Verify the query was executed
        mock_db_session.query.assert_called_with("SomeModel")
        assert result == test_object

    def test_mock_db_error_handling(self, mock_db_session):
        """Test how mock database handles errors."""
        # Simulate a database error
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Test that the error is raised
        with pytest.raises(Exception, match="Database error"):
            mock_db_session.commit()
        
        # Verify the error was called
        mock_db_session.commit.assert_called_once()

    def test_mock_db_query_chaining(self, mock_db_session):
        """Test chaining database queries with mock."""
        # Set up mock query chain
        mock_filter = Mock()
        mock_filter.first.return_value = "test_result"
        mock_query = Mock()
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        # Execute chained query
        result = mock_db_session.query("TestModel").filter().first()
        
        # Verify the chain was executed correctly
        mock_db_session.query.assert_called_with("TestModel")
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()
        assert result == "test_result" 