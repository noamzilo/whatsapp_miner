#!/usr/bin/env python3
"""
Test MessageClassifier

Tests for the MessageClassifier class with proper assertions and mocking.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.message_classification.message_classifier import MessageClassifier, ClassificationResult


class TestMessageClassifier:
    """Test cases for MessageClassifier."""

    @pytest.fixture
    def mock_classifier(self):
        """Create a MessageClassifier with mocked dependencies."""
        with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
            with patch('src.message_classification.message_classifier.get_db_session') as mock_db_session:
                with patch('src.message_classification.message_classifier.groq_api_key', 'test_key'):
                    with patch('src.message_classification.message_classifier.message_classifier_run_every_seconds', 30):
                        # Mock the database session
                        mock_session = Mock()
                        mock_db_session.return_value.__enter__.return_value = mock_session
                        mock_db_session.return_value.__exit__.return_value = None
                        
                        # Mock the prompt query
                        mock_prompt = Mock()
                        mock_prompt.prompt_text = """You are a classifier for WhatsApp messages from local groups. Your task is to determine if a message represents someone looking for a local service.

Services can include: dentist, spanish classes, restaurants, tutors, plumbers, electricians, and any other local business or service.

Analyze the message and respond with a JSON object containing:
- is_lead: boolean indicating if this is a lead
- lead_category: string describing the category (if it's a lead)
- lead_description: string describing what they're looking for (if it's a lead)
- confidence_score: float between 0 and 1
- reasoning: string explaining your classification

Message: {message_text}"""
                        
                        mock_session.query.return_value.filter.return_value.first.return_value = mock_prompt
                        
                        # Mock the LLM
                        mock_llm = Mock()
                        mock_chat_groq.return_value = mock_llm
                        
                        classifier = MessageClassifier()
                        yield classifier, mock_llm, mock_session

    def test_classifier_initialization(self, mock_classifier):
        """Test that MessageClassifier initializes correctly."""
        classifier, mock_llm, mock_session = mock_classifier
        
        assert classifier.llm is not None
        assert classifier.output_parser is not None
        assert classifier.classification_prompt is not None
        assert "is_lead" in classifier.classification_prompt
        assert "lead_category" in classifier.classification_prompt

    def test_classify_message_lead(self, mock_classifier):
        """Test classifying a message that should be identified as a lead."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM response for a lead
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.9,
            "reasoning": "Message clearly asks for dentist recommendations"
        }'''
        mock_llm.invoke.return_value = mock_response
        
        # Test message
        test_message = "Hi everyone! I'm looking for a good dentist in the area. Any recommendations?"
        
        result = classifier._classify_message(test_message)
        
        # Assertions
        assert result.is_lead is True
        assert result.lead_category == "dentist"
        assert result.lead_description == "Looking for a dentist"
        assert result.confidence_score == 0.9
        assert result.reasoning == "Message clearly asks for dentist recommendations"
        
        # Verify LLM was called
        mock_llm.invoke.assert_called_once()

    def test_classify_message_non_lead(self, mock_classifier):
        """Test classifying a message that should not be identified as a lead."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM response for a non-lead
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": false,
            "lead_category": null,
            "lead_description": null,
            "confidence_score": 0.8,
            "reasoning": "This is just a general conversation message"
        }'''
        mock_llm.invoke.return_value = mock_response
        
        # Test message
        test_message = "Just checking in to see how everyone is doing today!"
        
        result = classifier._classify_message(test_message)
        
        # Assertions
        assert result.is_lead is False
        assert result.lead_category is None
        assert result.lead_description is None
        assert result.confidence_score == 0.8
        assert result.reasoning == "This is just a general conversation message"

    def test_classify_message_error_handling(self, mock_classifier):
        """Test that classification handles errors gracefully."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM to raise an exception
        mock_llm.invoke.side_effect = Exception("API Error")
        
        test_message = "Test message"
        
        result = classifier._classify_message(test_message)
        
        # Should return a default classification with error reasoning
        assert result.is_lead is False
        assert result.lead_category is None
        assert result.lead_description is None
        assert result.confidence_score == 0.0
        assert "Error in classification" in result.reasoning

    def test_classify_message_invalid_json(self, mock_classifier):
        """Test handling of invalid JSON response from LLM."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM to return invalid JSON
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        mock_llm.invoke.return_value = mock_response
        
        test_message = "Test message"
        
        result = classifier._classify_message(test_message)
        
        # Should return a default classification
        assert result.is_lead is False
        assert result.lead_category is None
        assert result.lead_description is None
        assert result.confidence_score == 0.0
        assert "Error in classification" in result.reasoning

    def test_classify_message_missing_fields(self, mock_classifier):
        """Test handling of JSON response with missing fields."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM to return incomplete JSON
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": true,
            "confidence_score": 0.7
        }'''
        mock_llm.invoke.return_value = mock_response
        
        test_message = "Test message"
        
        result = classifier._classify_message(test_message)
        
        # Should parse the available fields from malformed JSON
        assert result.is_lead is True  # The JSON had "is_lead": true
        assert result.lead_category is None
        assert result.lead_description is None
        assert result.confidence_score == 0.7  # The JSON had "confidence_score": 0.7
        assert "Parsed from malformed response" in result.reasoning

    @pytest.mark.parametrize("message,expected_lead", [
        ("Looking for a dentist", True),
        ("Can anyone recommend a good restaurant?", True),
        ("Hi everyone, how are you?", False),
        ("Just checking in", False),
        ("Need a plumber urgently", True),
        ("Happy birthday!", False),
    ])
    def test_classify_various_messages(self, mock_classifier, message, expected_lead):
        """Test classification of various message types."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM response based on expected result
        mock_response = Mock()
        if expected_lead:
            mock_response.content = '''{
                "is_lead": true,
                "lead_category": "service",
                "lead_description": "Looking for a service",
                "confidence_score": 0.8,
                "reasoning": "Message asks for recommendations"
            }'''
        else:
            mock_response.content = '''{
                "is_lead": false,
                "lead_category": null,
                "lead_description": null,
                "confidence_score": 0.9,
                "reasoning": "General conversation message"
            }'''
        
        mock_llm.invoke.return_value = mock_response
        
        result = classifier._classify_message(message)
        
        # Basic assertion that the result matches expected lead status
        # Note: In a real test, you'd want to mock the LLM to return appropriate responses
        # based on the actual message content, but for this test we're using the parametrized expected_lead
        assert result.is_lead == expected_lead

    def test_classification_prompt_formatting(self, mock_classifier):
        """Test that the classification prompt is properly formatted."""
        classifier, mock_llm, mock_session = mock_classifier
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": false,
            "lead_category": null,
            "lead_description": null,
            "confidence_score": 0.5,
            "reasoning": "Test"
        }'''
        mock_llm.invoke.return_value = mock_response
        
        test_message = "Test message content"
        
        # Call the method that formats the prompt
        result = classifier._classify_message(test_message)
        
        # Verify that the LLM was called with properly formatted messages
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]
        
        # Should have SystemMessage and HumanMessage
        assert len(call_args) == 2
        assert "SystemMessage" in str(type(call_args[0]))
        assert "HumanMessage" in str(type(call_args[1]))
        
        # The human message should contain our test message
        assert test_message in str(call_args[1]) 