#!/usr/bin/env python3
"""
Debug Test for Hanging Issues

This test helps identify exactly where the hanging occurs in the classification process.
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


class TestDebugHanging:
    """Debug tests to identify hanging points."""

    def test_debug_classifier_initialization(self, classifier_with_test_db):
        """Test that classifier initialization doesn't hang."""
        try:
            with timeout_context(10):  # 10 second timeout
                classifier, test_db, mock_llm = classifier_with_test_db
                print("✅ Classifier initialization successful")
        except TimeoutError:
            pytest.fail("❌ Classifier initialization timed out")

    def test_debug_database_operations(self, classifier_with_test_db, test_data_factory):
        """Test that database operations don't hang."""
        classifier, test_db, mock_llm = classifier_with_test_db

        try:
            with timeout_context(10):  # 10 second timeout
                # Test database session
                print("🔍 Testing database session...")
                session = test_db.session
                print("✅ Database session created")

                # Test creating test data
                print("🔍 Testing test data creation...")
                user = test_data_factory.create_test_user(session)
                group = test_data_factory.create_test_group(session)
                message = test_data_factory.create_test_message(
                    session,
                    sender_id=user.id,
                    group_id=group.id,
                    raw_text="Test message",
                    llm_processed=False
                )
                print("✅ Test data created successfully")

                # Test querying unclassified messages
                print("🔍 Testing unclassified messages query...")
                unclassified = classifier._get_unclassified_messages(session)
                print(f"✅ Found {len(unclassified)} unclassified messages")

        except TimeoutError:
            pytest.fail("❌ Database operations timed out")

    def test_debug_llm_mocking(self, classifier_with_test_db):
        """Test that LLM mocking works correctly."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Ensure the mock is applied
        classifier.llm = mock_llm

        # Mock the response
        mock_response = Mock()
        mock_response.content = '''{
            "is_lead": true,
            "lead_category": "test",
            "lead_description": "Test lead",
            "confidence_score": 0.9,
            "reasoning": "Test reasoning"
        }'''
        mock_llm.invoke.return_value = mock_response

        try:
            with timeout_context(10):  # 10 second timeout
                print("🔍 Testing LLM classification...")
                result = classifier._classify_message("Test message")
                print("✅ LLM classification successful")
                print(f"   Result: {result}")

        except TimeoutError:
            pytest.fail("❌ LLM classification timed out")

    def test_debug_full_classification_step_by_step(self, classifier_with_test_db, test_data_factory):
        """Test the full classification process step by step."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a dentist",
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
        classifier.llm = mock_llm

        try:
            with timeout_context(30):  # 30 second timeout
                print("🔍 Step 1: Getting unclassified messages...")
                unclassified = classifier._get_unclassified_messages(test_db.session)
                print(f"✅ Found {len(unclassified)} unclassified messages")

                if unclassified:
                    print("🔍 Step 2: Classifying first message...")
                    classification_result = classifier._classify_message(unclassified[0].raw_text)
                    print("✅ Message classification successful")

                    print("🔍 Step 3: Creating classification record...")
                    classification = classifier._create_classification_record(
                        test_db.session, unclassified[0], classification_result
                    )
                    print("✅ Classification record created")

                    if classification_result.is_lead:
                        print("🔍 Step 4: Creating lead record...")
                        lead = classifier._create_lead_record(
                            test_db.session, unclassified[0], classification, classification_result
                        )
                        print("✅ Lead record created")

                    print("🔍 Step 5: Marking message as processed...")
                    classifier._mark_message_as_processed(test_db.session, unclassified[0])
                    print("✅ Message marked as processed")

        except TimeoutError:
            pytest.fail("❌ Step-by-step classification timed out")

    def test_debug_classify_messages_method(self, classifier_with_test_db, test_data_factory):
        """Test the classify_messages method with minimal data."""
        classifier, test_db, mock_llm = classifier_with_test_db

        # Create minimal test data
        user = test_data_factory.create_test_user(test_db.session)
        group = test_data_factory.create_test_group(test_db.session)
        message = test_data_factory.create_test_message(
            test_db.session,
            sender_id=user.id,
            group_id=group.id,
            raw_text="Looking for a dentist",
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
        classifier.llm = mock_llm

        try:
            with timeout_context(30):  # 30 second timeout
                print("🔍 Testing classify_messages method...")
                classifier.classify_messages()
                print("✅ classify_messages completed successfully")

        except TimeoutError:
            pytest.fail("❌ classify_messages method timed out") 