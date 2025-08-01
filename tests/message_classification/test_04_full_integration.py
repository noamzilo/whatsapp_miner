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
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Hi everyone! How are you all doing today?",
            llm_processed=False
        )
        
        # Mock the LLM response for a non-lead
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": false,
            "lead_category": null,
            "lead_description": null,
            "confidence_score": 0.8,
            "reasoning": "This is just a general conversation message"
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
        assert classification.confidence_score == 0.8
        assert classification.raw_llm_output['is_lead'] is False
        assert classification.raw_llm_output['lead_category'] is None
        
        # Verify NO lead record was created
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).filter_by(
            classification_id=classification.id
        ).all()
        assert len(leads) == 0
        
        # Verify general category was created
        from src.db.models.lead_category import LeadCategory
        categories = test_db.session.query(LeadCategory).filter_by(name="general").all()
        assert len(categories) == 1
        
        # Verify intent type was created
        from src.db.models.message_intent_type import MessageIntentType
        intent_types = test_db.session.query(MessageIntentType).filter_by(name="general_message").all()
        assert len(intent_types) == 1
    
    def test_multiple_messages_classification(self, classifier_with_test_db, test_data_factory):
        """
        Test classification of multiple messages in a single run.
        
        This test verifies:
        1. Multiple messages are processed correctly
        2. Each message gets its own classification record
        3. Lead records are created only for lead messages
        4. All messages are marked as processed
        """
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        
        # Create multiple unclassified messages
        messages = [
            test_data_factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="Looking for a good dentist in the area",
                llm_processed=False
            ),
            test_data_factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="Hi everyone! How are you?",
                llm_processed=False
            ),
            test_data_factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="Need a plumber urgently, any recommendations?",
                llm_processed=False
            )
        ]
        
        # Mock the LLM responses
        mock_llm.invoke.side_effect = [
            Mock(content='''{
                "is_lead": true,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message asks for dentist recommendations"
            }'''),
            Mock(content='''{
                "is_lead": false,
                "lead_category": null,
                "lead_description": null,
                "confidence_score": 0.8,
                "reasoning": "General conversation message"
            }'''),
            Mock(content='''{
                "is_lead": true,
                "lead_category": "plumber",
                "lead_description": "Looking for a plumber",
                "confidence_score": 0.95,
                "reasoning": "Message urgently asks for plumber recommendations"
            }''')
        ]
        
        # Run the classification
        classifier.classify_messages()
        
        # Verify all messages were processed
        for message in messages:
            test_db.session.refresh(message)
            assert message.llm_processed is True
        
        # Verify classification records were created
        from src.db.models.message_intent_classification import MessageIntentClassification
        classifications = test_db.session.query(MessageIntentClassification).all()
        assert len(classifications) == 3
        
        # Verify lead records were created only for lead messages
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).all()
        assert len(leads) == 2
        
        # Verify categories were created
        from src.db.models.lead_category import LeadCategory
        categories = test_db.session.query(LeadCategory).all()
        category_names = [cat.name for cat in categories]
        assert "dentist" in category_names
        assert "plumber" in category_names
        assert "general" in category_names
        
        # Verify intent types were created
        from src.db.models.message_intent_type import MessageIntentType
        intent_types = test_db.session.query(MessageIntentType).all()
        intent_names = [intent.name for intent in intent_types]
        assert "lead_seeking" in intent_names
        assert "general_message" in intent_names
    
    def test_classification_with_existing_categories(self, classifier_with_test_db, test_data_factory):
        """
        Test classification when categories already exist in the database.
        
        This test verifies:
        1. Existing categories are reused
        2. No duplicate categories are created
        3. Classification still works correctly
        """
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        
        # Pre-create categories
        from src.db.models.lead_category import LeadCategory
        from src.db.models.message_intent_type import MessageIntentType
        
        existing_category = LeadCategory(
            name="dentist",
            description="Category for dentist leads",
            opening_message_template="Hi! I saw you're looking for dentist services. How can I help?"
        )
        test_db.session.add(existing_category)
        
        existing_intent = MessageIntentType(
            name="lead_seeking",
            description="Intent type for lead seeking"
        )
        test_db.session.add(existing_intent)
        test_db.session.commit()
        
        # Create an unclassified message
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a good dentist in the area",
            llm_processed=False
        )
        
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.9,
            "reasoning": "Message asks for dentist recommendations"
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
        assert classification.lead_category_id == existing_category.id  # Should use existing category
        assert classification.intent_type_id == existing_intent.id      # Should use existing intent type
        
        # Verify lead record was created
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).filter_by(
            classification_id=classification.id
        ).all()
        assert len(leads) == 1
        
        # Verify no new categories were created (should reuse existing)
        categories = test_db.session.query(LeadCategory).all()
        assert len(categories) == 2  # 1 existing + 1 general (created for non-leads)
        
        intent_types = test_db.session.query(MessageIntentType).all()
        assert len(intent_types) == 2  # 1 existing + 1 general_message (created for non-leads)
    
    def test_classification_error_handling(self, classifier_with_test_db, test_data_factory):
        """
        Test classification error handling.
        
        This test verifies:
        1. Errors in classification don't crash the entire process
        2. Failed messages remain unprocessed
        3. Successful messages are still processed
        """
        classifier, test_db, mock_llm = classifier_with_test_db
        
        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        
        # Create messages - one that will succeed, one that will fail
        messages = [
            test_data_factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="Looking for a good dentist",
                llm_processed=False
            ),
            test_data_factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="This message will cause an error",
                llm_processed=False
            )
        ]
        
        # Mock the LLM to fail on the second message
        mock_llm.invoke.side_effect = [
            Mock(content='''{
                "is_lead": true,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message asks for dentist recommendations"
            }'''),
            Exception("LLM API error")  # This will cause the second message to fail
        ]
        
        # Run the classification
        classifier.classify_messages()
        
        # Verify only the first message was processed
        test_db.session.refresh(messages[0])
        test_db.session.refresh(messages[1])
        
        # First message should be processed
        assert messages[0].llm_processed is True
        
        # Second message should remain unprocessed due to error
        assert messages[1].llm_processed is False
        
        # Verify only one classification record was created
        from src.db.models.message_intent_classification import MessageIntentClassification
        classifications = test_db.session.query(MessageIntentClassification).all()
        assert len(classifications) == 1
        
        # Verify only one lead record was created
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).all()
        assert len(leads) == 1 