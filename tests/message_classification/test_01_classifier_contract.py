#!/usr/bin/env python3
"""
Level 1: Classifier Contract Tests

Tests the MessageClassifier contract and interface with full mocking.
These are the smallest test blocks that verify the basic functionality.
"""

import pytest
from unittest.mock import Mock


class TestClassifierContract:
    """Test the MessageClassifier contract and interface."""
    
    def test_classifier_initialization(self, mock_classifier):
        """Test that MessageClassifier initializes correctly."""
        assert mock_classifier.llm is not None
        assert mock_classifier.output_parser is not None
        assert mock_classifier.classification_prompt is not None
        # The classification_prompt is the actual prompt text, not a dict
        assert "is_lead" in mock_classifier.classification_prompt or "lead" in mock_classifier.classification_prompt
    
    def test_classification_result_structure(self, sample_classification_result):
        """Test that ClassificationResult has the correct structure."""
        assert hasattr(sample_classification_result, 'is_lead')
        assert hasattr(sample_classification_result, 'lead_category')
        assert hasattr(sample_classification_result, 'lead_description')
        assert hasattr(sample_classification_result, 'confidence_score')
        assert hasattr(sample_classification_result, 'reasoning')
        
        assert sample_classification_result.is_lead is True
        assert sample_classification_result.lead_category == "dentist"
        assert sample_classification_result.confidence_score == 0.9
    
    def test_non_lead_classification_result_structure(self, sample_non_lead_classification_result):
        """Test that non-lead ClassificationResult has the correct structure."""
        assert sample_non_lead_classification_result.is_lead is False
        assert sample_non_lead_classification_result.lead_category is None
        assert sample_non_lead_classification_result.lead_description is None
        assert sample_non_lead_classification_result.confidence_score == 0.8
    
    def test_classifier_has_required_methods(self, mock_classifier):
        """Test that MessageClassifier has all required methods."""
        required_methods = [
            '_get_classification_prompt',
            '_get_unclassified_messages',
            '_classify_message',
            '_get_or_create_lead_category',
            '_get_or_create_intent_type',
            '_create_classification_record',
            '_create_lead_record',
            '_mark_message_as_processed',
            'classify_messages',
            'run_continuous'
        ]
        
        for method_name in required_methods:
            assert hasattr(mock_classifier, method_name), f"Missing method: {method_name}"
    
    def test_classifier_prompt_retrieval(self, mock_classifier, mock_db_session):
        """Test that the classifier can retrieve prompts from database."""
        # Mock the prompt query
        mock_prompt = Mock()
        mock_prompt.prompt_text = "Test classification prompt"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        prompt = mock_classifier._get_classification_prompt()
        assert prompt == "Test classification prompt"
    
    def test_classifier_unclassified_messages_retrieval(self, mock_classifier, mock_db_session):
        """Test that the classifier can retrieve unclassified messages."""
        # Mock unclassified messages
        mock_message1 = Mock()
        mock_message1.id = 1
        mock_message1.llm_processed = False
        
        mock_message2 = Mock()
        mock_message2.id = 2
        mock_message2.llm_processed = False
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_message1, mock_message2]
        
        unclassified = mock_classifier._get_unclassified_messages(mock_db_session)
        assert len(unclassified) == 2
        assert unclassified[0].id == 1
        assert unclassified[1].id == 2
    
    def test_classifier_lead_category_creation(self, mock_classifier, mock_db_session):
        """Test that the classifier can create lead categories."""
        # Mock that no category exists initially
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        category = mock_classifier._get_or_create_lead_category(mock_db_session, "dentist")
        
        # Verify the category was created
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_classifier_intent_type_creation(self, mock_classifier, mock_db_session):
        """Test that the classifier can create intent types."""
        # Mock that no intent type exists initially
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        intent_type = mock_classifier._get_or_create_intent_type(mock_db_session, "lead_seeking")
        
        # Verify the intent type was created
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_classifier_message_processing_mark(self, mock_classifier, mock_db_session):
        """Test that the classifier can mark messages as processed."""
        mock_message = Mock()
        mock_message.llm_processed = False
        
        mock_classifier._mark_message_as_processed(mock_db_session, mock_message)
        
        assert mock_message.llm_processed is True
        mock_db_session.commit.assert_called()
    
    def test_classifier_lead_record_creation(self, mock_classifier, mock_db_session):
        """Test that the classifier can create lead records."""
        # Mock required objects
        mock_message = Mock()
        mock_message.sender_id = 1
        mock_message.group_id = 1
        
        mock_classification = Mock()
        mock_classification.id = 1
        
        mock_classification_result = Mock()
        mock_classification_result.lead_description = "Looking for a dentist"
        
        lead = mock_classifier._create_lead_record(
            mock_db_session, 
            mock_message, 
            mock_classification, 
            mock_classification_result
        )
        
        # Verify the lead record was created
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
    
    def test_classifier_classification_record_creation(self, mock_classifier, mock_db_session):
        """Test that the classifier can create classification records."""
        # Mock required objects
        mock_message = Mock()
        mock_message.id = 1
        
        mock_classification_result = Mock()
        mock_classification_result.is_lead = True
        mock_classification_result.lead_category = "dentist"
        mock_classification_result.confidence_score = 0.9
        mock_classification_result.model_dump.return_value = {"test": "data"}
        
        # Mock category and intent type creation
        mock_category = Mock()
        mock_category.id = 1
        mock_intent_type = Mock()
        mock_intent_type.id = 1
        mock_prompt = Mock()
        mock_prompt.id = 1
        
        mock_classifier._get_or_create_lead_category = Mock(return_value=mock_category)
        mock_classifier._get_or_create_intent_type = Mock(return_value=mock_intent_type)
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
        
        classification = mock_classifier._create_classification_record(
            mock_db_session, 
            mock_message, 
            mock_classification_result
        )
        
        # Verify the classification record was created
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called() 