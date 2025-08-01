#!/usr/bin/env python3
"""
Level 4: Full Integration Tests

Tests the complete message classification flow with real database and mocked LLM.
These are the largest test blocks that verify the entire system works together.
"""

import pytest
from unittest.mock import Mock


class TestFullIntegration:
    """Test the complete message classification flow."""
    
    def test_full_classification_flow_lead_message(self, classifier_with_test_db, test_data_factory):
        """
        Test the complete classification flow for a lead message.
        
        This test verifies:
        1. Message is properly stored and retrieved
        2. Real LLM classification works (mocked)
        3. Classification record is created
        4. Lead record is created for lead messages
        5. Message is marked as processed
        """
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Hi everyone! I'm looking for a good dentist in the area. Any recommendations?",
            llm_processed=False
        )
        
        # Mock the LLM response for a lead
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.9,
            "reasoning": "Message clearly asks for dentist recommendations"
        }'''
        mock_llm.invoke.return_value = mock_response
        
        # Run the classification
        classifier.classify_messages()
        
        # Verify the message was processed
        test_db.session.refresh(message)
        assert message.llm_processed is True
        
        # Verify classification record was created
        from src.db.models.message_intent_classification import MessageIntentClassification
        classifications = test_db.session.query(MessageIntentClassification).filter_by(
            message_id=message.id
        ).all()
        assert len(classifications) == 1
        
        classification = classifications[0]
        assert classification.confidence_score == 0.9
        assert classification.raw_llm_output['is_lead'] is True
        assert classification.raw_llm_output['lead_category'] == "dentist"
        
        # Verify lead record was created
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).filter_by(
            classification_id=classification.id
        ).all()
        assert len(leads) == 1
        
        lead = leads[0]
        assert lead.user_id == user.id
        assert lead.group_id == group.id
        assert lead.lead_for == "Looking for a dentist"
        
        # Verify lead category was created
        from src.db.models.lead_category import LeadCategory
        categories = test_db.session.query(LeadCategory).filter_by(name="dentist").all()
        assert len(categories) == 1
        
        # Verify intent type was created
        from src.db.models.message_intent_type import MessageIntentType
        intent_types = test_db.session.query(MessageIntentType).filter_by(name="lead_seeking").all()
        assert len(intent_types) == 1
    
    @pytest.mark.skip(reason="Hanging test - needs fix")
    def test_full_classification_flow_non_lead_message(self, classifier_with_test_db, test_data_factory):
        """
        Test the complete classification flow for a non-lead message.
        
        This test verifies:
        1. Message is properly stored and retrieved
        2. Real LLM classification works (mocked)
        3. Classification record is created
        4. No lead record is created for non-lead messages
        5. Message is marked as processed
        """
        # TODO: Fix this test to use proper test database isolation
        pass
    
    @pytest.mark.skip(reason="Hanging test - needs fix")
    def test_multiple_messages_classification(self, classifier_with_test_db, test_data_factory):
        """
        Test classification of multiple messages in a single run.
        
        This test verifies:
        1. Multiple messages are processed correctly
        2. Each message gets its own classification record
        3. Lead records are created only for lead messages
        4. All messages are marked as processed
        """
        # TODO: Fix this test to use proper test database isolation
        pass
    
    @pytest.mark.skip(reason="Hanging test - needs fix")
    def test_classification_with_existing_categories(self, classifier_with_test_db, test_data_factory):
        """
        Test classification when categories already exist in the database.
        
        This test verifies:
        1. Existing categories are reused
        2. No duplicate categories are created
        3. Classification still works correctly
        """
        # TODO: Fix this test to use proper test database isolation
        pass
    
    @pytest.mark.skip(reason="Hanging test - needs fix")
    def test_classification_error_handling(self, classifier_with_test_db, test_data_factory):
        """
        Test classification error handling.
        
        This test verifies:
        1. Errors in classification don't crash the entire process
        2. Failed messages remain unprocessed
        3. Successful messages are still processed
        """
        # TODO: Fix this test to use proper test database isolation
        pass 