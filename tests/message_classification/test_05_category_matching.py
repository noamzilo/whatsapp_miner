#!/usr/bin/env python3
"""
Level 5: Category Matching Tests

Tests the category matching functionality that tries to match messages with existing categories
before creating new ones.
"""

import pytest
from unittest.mock import Mock, patch
from contextlib import contextmanager


@contextmanager
def timeout_context(seconds: int):
    """Context manager to add timeout to operations."""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up signal handler for timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class TestCategoryMatching:
    """Test category matching functionality."""

    def test_match_with_existing_category(self, classifier_with_test_db, test_data_factory):
        """Test that messages are matched to existing categories when possible."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create existing categories
        from src.db.models.lead_category import LeadCategory
        dentist_category = LeadCategory(
            name="dentist",
            description="Category for dentist leads",
            opening_message_template="Hi! I saw you're looking for dentist services. How can I help?"
        )
        plumber_category = LeadCategory(
            name="plumber",
            description="Category for plumber leads",
            opening_message_template="Hi! I saw you're looking for plumber services. How can I help?"
        )
        test_db.session.add(dentist_category)
        test_db.session.add(plumber_category)
        test_db.session.commit()

        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="I need a good dentist in the area, any recommendations?",
            llm_processed=False
        )

        # Mock the LLM responses
        # First call: Main classification
        classification_response = Mock()
        classification_response.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.9,
            "reasoning": "Message asks for dentist recommendations"
        }'''
        
        # Second call: Category matching (uses original message text)
        matching_response = Mock()
        matching_response.content = "dentist"
        
        mock_llm.invoke.side_effect = [classification_response, matching_response]

        # Ensure the mock is applied to the classifier's LLM instance
        classifier.llm = mock_llm

        # Mock the database session to use test database
        with patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
            # Create a context manager that returns the test session
            class TestSessionContext:
                def __enter__(self):
                    return test_db.session
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            mock_get_session.return_value = TestSessionContext()

            # Run the classification with timeout
            try:
                with timeout_context(30):  # 30 second timeout
                    classifier.classify_messages()
            except TimeoutError:
                pytest.fail("Test timed out - likely hanging on LLM call or database operation")

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

        # Verify the classification used the existing category (not created a new one)
        assert classification.lead_category_id == dentist_category.id

        # Verify lead record was created
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).filter_by(
            classification_id=classification.id
        ).all()
        assert len(leads) == 1

        # Verify that the category matching was called with the original message text
        assert mock_llm.invoke.call_count == 2
        # The second call should be for category matching with the original message
        second_call_args = mock_llm.invoke.call_args_list[1][0][0]
        assert "Original message: I need a good dentist in the area, any recommendations?" in str(second_call_args)

    def test_no_match_with_existing_categories(self, classifier_with_test_db, test_data_factory):
        """Test that new categories are created when no match is found."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create existing categories
        from src.db.models.lead_category import LeadCategory
        dentist_category = LeadCategory(
            name="dentist",
            description="Category for dentist leads",
            opening_message_template="Hi! I saw you're looking for dentist services. How can I help?"
        )
        test_db.session.add(dentist_category)
        test_db.session.commit()

        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="I need a good electrician for my house wiring",
            llm_processed=False
        )

        # Mock the LLM responses
        # First call: Main classification
        classification_response = Mock()
        classification_response.content = '''{
            "is_lead": true,
            "lead_category": "electrician",
            "lead_description": "Looking for an electrician",
            "confidence_score": 0.9,
            "reasoning": "Message asks for electrician recommendations"
        }'''
        
        # Second call: Category matching (no match found)
        matching_response = Mock()
        matching_response.content = "no_match"
        
        mock_llm.invoke.side_effect = [classification_response, matching_response]

        # Ensure the mock is applied to the classifier's LLM instance
        classifier.llm = mock_llm

        # Mock the database session to use test database
        with patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
            # Create a context manager that returns the test session
            class TestSessionContext:
                def __enter__(self):
                    return test_db.session
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            mock_get_session.return_value = TestSessionContext()

            # Run the classification with timeout
            try:
                with timeout_context(30):  # 30 second timeout
                    classifier.classify_messages()
            except TimeoutError:
                pytest.fail("Test timed out - likely hanging on LLM call or database operation")

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
        assert classification.raw_llm_output['lead_category'] == "electrician"

        # Verify a new category was created
        new_category = test_db.session.query(LeadCategory).filter_by(name="electrician").first()
        assert new_category is not None
        assert classification.lead_category_id == new_category.id

    def test_short_message_auto_classification(self, classifier_with_test_db, test_data_factory):
        """Test that messages under 8 characters are automatically classified as non-leads."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create test data with short message
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Hi",  # Under 8 characters
            llm_processed=False
        )

        # Mock the LLM (should not be called for short messages)
        mock_llm.invoke.return_value = Mock()

        # Ensure the mock is applied to the classifier's LLM instance
        classifier.llm = mock_llm

        # Mock the database session to use test database
        with patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
            # Create a context manager that returns the test session
            class TestSessionContext:
                def __enter__(self):
                    return test_db.session
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            mock_get_session.return_value = TestSessionContext()

            # Run the classification with timeout
            try:
                with timeout_context(30):  # 30 second timeout
                    classifier.classify_messages()
            except TimeoutError:
                pytest.fail("Test timed out - likely hanging on LLM call or database operation")

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
        assert classification.confidence_score == 1.0
        assert classification.raw_llm_output['is_lead'] is False
        assert classification.raw_llm_output['reasoning'] == "Message too short (under 8 characters) to be a lead"

        # Verify no lead record was created
        from src.db.models.detected_lead import DetectedLead
        leads = test_db.session.query(DetectedLead).filter_by(
            classification_id=classification.id
        ).all()
        assert len(leads) == 0

        # Verify LLM was not called (short message handled automatically)
        mock_llm.invoke.assert_not_called()

    def test_category_matching_error_handling(self, classifier_with_test_db, test_data_factory):
        """Test that category matching errors don't break the classification process."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create existing categories
        from src.db.models.lead_category import LeadCategory
        dentist_category = LeadCategory(
            name="dentist",
            description="Category for dentist leads",
            opening_message_template="Hi! I saw you're looking for dentist services. How can I help?"
        )
        test_db.session.add(dentist_category)
        test_db.session.commit()

        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="I need a good dentist in the area",
            llm_processed=False
        )

        # Mock the LLM responses
        # First call: Main classification
        classification_response = Mock()
        classification_response.content = '''{
            "is_lead": true,
            "lead_category": "dentist",
            "lead_description": "Looking for a dentist",
            "confidence_score": 0.9,
            "reasoning": "Message asks for dentist recommendations"
        }'''
        
        # Second call: Category matching (throws error)
        matching_response = Mock()
        matching_response.side_effect = Exception("LLM API Error")
        
        mock_llm.invoke.side_effect = [classification_response, matching_response]

        # Ensure the mock is applied to the classifier's LLM instance
        classifier.llm = mock_llm

        # Mock the database session to use test database
        with patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
            # Create a context manager that returns the test session
            class TestSessionContext:
                def __enter__(self):
                    return test_db.session
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            mock_get_session.return_value = TestSessionContext()

            # Run the classification with timeout
            try:
                with timeout_context(30):  # 30 second timeout
                    classifier.classify_messages()
            except TimeoutError:
                pytest.fail("Test timed out - likely hanging on LLM call or database operation")

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

        # Verify a new category was created (fallback when matching fails)
        new_category = test_db.session.query(LeadCategory).filter_by(name="dentist").first()
        assert new_category is not None
        assert classification.lead_category_id == new_category.id 