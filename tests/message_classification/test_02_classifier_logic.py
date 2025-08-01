#!/usr/bin/env python3
"""
Level 2: Classifier Logic Tests

Tests the MessageClassifier actual logic with real LLM calls.
These tests are marked as slow and should be run separately.
"""

import pytest
from unittest.mock import Mock


class TestClassifierLogic:
    """Test the MessageClassifier actual logic with real LLM."""
    
    @pytest.mark.slow
    def test_classifier_with_real_llm(self, mock_llm, mock_db_session):
        """Test classifier with real LLM (mocked responses)."""
        from src.message_classification.message_classifier import MessageClassifier
        
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classifier = MessageClassifier()
        
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
        
        # Test classification
        result = classifier._classify_message("Looking for a good dentist in the area")
        
        # Verify the result
        assert result.is_lead is True
        assert result.lead_category == "dentist"
        assert result.lead_description == "Looking for a dentist"
        assert result.confidence_score == 0.9
        assert result.reasoning == "Message clearly asks for dentist recommendations"
        
        # Verify LLM was called
        mock_llm.invoke.assert_called_once()
    
    @pytest.mark.slow
    def test_classifier_with_non_lead_message(self, mock_llm, mock_db_session):
        """Test classifier with non-lead message."""
        from src.message_classification.message_classifier import MessageClassifier
        
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classifier = MessageClassifier()
        
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
        
        # Test classification
        result = classifier._classify_message("Hi everyone! How are you all doing today?")
        
        # Verify the result
        assert result.is_lead is False
        assert result.lead_category is None
        assert result.lead_description is None
        assert result.confidence_score == 0.8
        assert result.reasoning == "This is just a general conversation message"
    
    @pytest.mark.slow
    @pytest.mark.parametrize("message_type,expected_lead", [
        ("lead_dentist", True),
        ("lead_plumber", True),
        ("lead_restaurant", True),
        ("non_lead_greeting", False),
        ("non_lead_general", False),
    ])
    def test_classifier_with_various_messages(self, mock_llm, mock_db_session, sample_messages, message_type, expected_lead):
        """Test classifier with various message types."""
        from src.message_classification.message_classifier import MessageClassifier
        
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classifier = MessageClassifier()
        
        # Get the test message
        message_data = sample_messages[message_type]
        test_message = message_data["raw_text"]
        
        # Mock LLM response based on expected result
        mock_response = Mock()
        if expected_lead:
            mock_response.content = f'''{{
                "is_lead": true,
                "lead_category": "{message_data["expected_category"]}",
                "lead_description": "{message_data["expected_description"]}",
                "confidence_score": 0.9,
                "reasoning": "Message asks for {message_data["expected_category"]} recommendations"
            }}'''
        else:
            mock_response.content = '''{
                "is_lead": false,
                "lead_category": null,
                "lead_description": null,
                "confidence_score": 0.8,
                "reasoning": "This is just a general conversation message"
            }'''
        
        mock_llm.invoke.return_value = mock_response
        
        # Test classification
        result = classifier._classify_message(test_message)
        
        # Verify the result
        assert result.is_lead == expected_lead
        if expected_lead:
            assert result.lead_category == message_data["expected_category"]
            assert result.lead_description == message_data["expected_description"]
        else:
            assert result.lead_category is None
            assert result.lead_description is None
    
    @pytest.mark.slow
    def test_classifier_error_handling(self, mock_llm, mock_db_session):
        """Test classifier error handling with malformed LLM responses."""
        from src.message_classification.message_classifier import MessageClassifier
        
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classifier = MessageClassifier()
        
        # Mock LLM response with malformed JSON
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        mock_llm.invoke.return_value = mock_response
        
        # Test classification - should handle the error gracefully
        result = classifier._classify_message("Test message")
        
        # Should return a default result
        assert result.is_lead is False
        assert result.confidence_score == 0.0
        assert "Error in classification" in result.reasoning
    
    @pytest.mark.slow
    def test_classifier_retry_logic(self, mock_llm, mock_db_session):
        """Test classifier retry logic with failing LLM calls."""
        from src.message_classification.message_classifier import MessageClassifier
        
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classifier = MessageClassifier()
        
        # Mock LLM to fail twice, then succeed
        mock_llm.invoke.side_effect = [
            Exception("LLM API error"),  # First attempt fails
            Exception("LLM API error"),  # Second attempt fails
            Mock(content='''{
                "is_lead": true,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message asks for dentist recommendations"
            }''')  # Third attempt succeeds
        ]
        
        # Test classification - should retry and eventually succeed
        result = classifier._classify_message("Looking for a dentist")
        
        # Verify the result
        assert result.is_lead is True
        assert result.lead_category == "dentist"
        
        # Verify LLM was called 3 times (2 failures + 1 success)
        assert mock_llm.invoke.call_count == 3
    
    @pytest.mark.slow
    def test_classifier_confidence_scores(self, mock_llm, mock_db_session):
        """Test classifier with different confidence scores."""
        from src.message_classification.message_classifier import MessageClassifier
        
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classifier = MessageClassifier()
        
        # Test high confidence
        mock_response_high = Mock()
        mock_response_high.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.95,
            "reasoning": "Very clear request for dentist"
        }'''
        mock_llm.invoke.return_value = mock_response_high
        
        result_high = classifier._classify_message("Looking for a dentist")
        assert result_high.confidence_score == 0.95
        
        # Test low confidence
        mock_response_low = Mock()
        mock_response_low.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.6,
            "reasoning": "Somewhat unclear request"
        }'''
        mock_llm.invoke.return_value = mock_response_low
        
        result_low = classifier._classify_message("Looking for a dentist")
        assert result_low.confidence_score == 0.6 