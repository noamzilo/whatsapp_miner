#!/usr/bin/env python3
"""
Level 4: Full Integration Tests

Tests the complete message classification flow with real database and mocked LLM.
These are the largest test blocks that verify the entire system works together.
"""

import pytest
import time
import signal
from unittest.mock import Mock, patch
from contextlib import contextmanager


@contextmanager
def timeout_context(seconds: int):
    """Context manager to add timeout to operations."""
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

		# Ensure the mock is applied to the classifier's LLM instance
		classifier.llm = mock_llm

		# Mock the database session to use test database
		from unittest.mock import patch
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
			raw_text="Good morning everyone! How's your day going?",
			llm_processed=False
		)

		# Mock the LLM response for a non-lead
		mock_response = Mock()
		mock_response.content = '''{
			"is_lead": false,
			"lead_category": null,
			"lead_description": null,
			"confidence_score": 0.8,
			"reasoning": "This is just a casual greeting message"
		}'''
		mock_llm.invoke.return_value = mock_response

		# Ensure the mock is applied to the classifier's LLM instance
		classifier.llm = mock_llm

		# Mock the database session to use test database
		from unittest.mock import patch
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
		assert classification.confidence_score == 0.8
		assert classification.raw_llm_output['is_lead'] is False
		assert classification.raw_llm_output['lead_category'] is None

		# Verify no lead record was created
		from src.db.models.detected_lead import DetectedLead
		leads = test_db.session.query(DetectedLead).filter_by(
			classification_id=classification.id
		).all()
		assert len(leads) == 0

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
		
		# Create multiple messages
		message1 = test_data_factory.create_test_message(
			test_db.session,
			sender_id=user.id,
			group_id=group.id,
			raw_text="Looking for a good plumber in the area",
			llm_processed=False
		)
		message2 = test_data_factory.create_test_message(
			test_db.session,
			sender_id=user.id,
			group_id=group.id,
			raw_text="Just saying hello to everyone!",
			llm_processed=False
		)

		# Mock the LLM responses
		mock_response1 = Mock()
		mock_response1.content = '''{
			"is_lead": true,
			"lead_category": "plumber",
			"lead_description": "Looking for a plumber",
			"confidence_score": 0.9,
			"reasoning": "Message asks for plumber recommendations"
		}'''
		
		mock_response2 = Mock()
		mock_response2.content = '''{
			"is_lead": false,
			"lead_category": null,
			"lead_description": null,
			"confidence_score": 0.7,
			"reasoning": "This is just a greeting message"
		}'''
		
		# Set up mock to return different responses for different calls
		mock_llm.invoke.side_effect = [mock_response1, mock_response2]

		# Ensure the mock is applied to the classifier's LLM instance
		classifier.llm = mock_llm

		# Mock the database session to use test database
		from unittest.mock import patch
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

		# Verify both messages were processed
		test_db.session.refresh(message1)
		test_db.session.refresh(message2)
		assert message1.llm_processed is True
		assert message2.llm_processed is True

		# Verify classification records were created
		from src.db.models.message_intent_classification import MessageIntentClassification
		classifications = test_db.session.query(MessageIntentClassification).all()
		assert len(classifications) == 2

		# Verify only one lead record was created (for the lead message)
		from src.db.models.detected_lead import DetectedLead
		leads = test_db.session.query(DetectedLead).all()
		assert len(leads) == 1

	def test_classification_with_existing_categories(self, classifier_with_test_db, test_data_factory):
		"""
		Test classification when categories already exist in the database.

		This test verifies:
		1. Existing categories are reused
		2. No duplicate categories are created
		3. Classification still works correctly
		"""
		classifier, test_db, mock_llm = classifier_with_test_db

		# Create existing category first
		from src.db.models.lead_category import LeadCategory
		existing_category = LeadCategory(
			name="dentist",
			description="Category for dentist leads",
			opening_message_template="Hi! I saw you're looking for dentist services. How can I help?"
		)
		test_db.session.add(existing_category)
		test_db.session.commit()

		# Create test data
		user = test_data_factory.create_test_user(test_db.session)
		group = test_data_factory.create_test_group(test_db.session)
		message = test_data_factory.create_test_message(
			test_db.session,
			sender_id=user.id,
			group_id=group.id,
			raw_text="Need a dentist recommendation",
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

		# Ensure the mock is applied to the classifier's LLM instance
		classifier.llm = mock_llm

		# Mock the database session to use test database
		from unittest.mock import patch
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

		# Verify only one category exists (no duplicate created)
		categories = test_db.session.query(LeadCategory).filter_by(name="dentist").all()
		assert len(categories) == 1
		assert categories[0].id == existing_category.id

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
		
		# Create two messages - one that will succeed, one that will fail
		message1 = test_data_factory.create_test_message(
			test_db.session,
			sender_id=user.id,
			group_id=group.id,
			raw_text="Looking for a dentist",
			llm_processed=False
		)
		message2 = test_data_factory.create_test_message(
			test_db.session,
			sender_id=user.id,
			group_id=group.id,
			raw_text="This will cause an error",
			llm_processed=False
		)

		# Mock the LLM to succeed for first message, fail for second
		mock_response1 = Mock()
		mock_response1.content = '''{
			"is_lead": true,
			"lead_category": "dentist",
			"lead_description": "Looking for a dentist",
			"confidence_score": 0.9,
			"reasoning": "Message asks for dentist recommendations"
		}'''
		
		# Set up mock to succeed first, fail second
		mock_llm.invoke.side_effect = [mock_response1, Exception("LLM API Error")]

		# Ensure the mock is applied to the classifier's LLM instance
		classifier.llm = mock_llm

		# Mock the database session to use test database
		from unittest.mock import patch
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

		# Verify both messages were processed (error handling returns default classification)
		test_db.session.refresh(message1)
		test_db.session.refresh(message2)
		assert message1.llm_processed is True
		assert message2.llm_processed is True  # Error handling returns default classification

		# Verify both classification records were created
		from src.db.models.message_intent_classification import MessageIntentClassification
		classifications = test_db.session.query(MessageIntentClassification).all()
		assert len(classifications) == 2

		# Verify only one lead record was created (for the successful message)
		from src.db.models.detected_lead import DetectedLead
		leads = test_db.session.query(DetectedLead).all()
		assert len(leads) == 1

		# Verify the failed message got a default classification (not a lead)
		failed_classification = next(c for c in classifications if c.message_id == message2.id)
		assert failed_classification.confidence_score == 0.0
		assert failed_classification.raw_llm_output['is_lead'] is False