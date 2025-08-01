#!/usr/bin/env python3
"""
Debug test to isolate hanging issues.
"""

import pytest
from unittest.mock import Mock


def test_simple_classifier_creation(classifier_with_test_db):
    """Simple test to see if classifier creation works."""
    classifier, test_db, mock_llm = classifier_with_test_db
    assert classifier is not None
    assert test_db is not None
    assert mock_llm is not None
    print("✓ Classifier creation works")


def test_simple_message_creation(classifier_with_test_db, test_data_factory):
    """Simple test to see if message creation works."""
    classifier, test_db, mock_llm = classifier_with_test_db
    
    # Create test data
    user = test_data_factory.create_test_user(test_db.session)
    group = test_data_factory.create_test_group(test_db.session)
    message = test_data_factory.create_test_message(
        test_db.session,
        sender_id=user.id,
        group_id=group.id,
        raw_text="Test message",
        llm_processed=False
    )
    
    assert message is not None
    assert message.llm_processed is False
    print("✓ Message creation works")


def test_simple_llm_mock(classifier_with_test_db, test_data_factory):
    """Simple test to see if LLM mocking works."""
    classifier, test_db, mock_llm = classifier_with_test_db
    
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
    
    # Test that the mock works
    result = mock_llm.invoke("test")
    assert result.content is not None
    print("✓ LLM mocking works")


def test_database_isolation(classifier_with_test_db, test_data_factory):
    """Test that we're using the test database, not the real database."""
    classifier, test_db, mock_llm = classifier_with_test_db
    
    # Create test data
    user = test_data_factory.create_test_user(test_db.session)
    group = test_data_factory.create_test_group(test_db.session)
    message = test_data_factory.create_test_message(
        test_db.session,
        sender_id=user.id,
        group_id=group.id,
        raw_text="Test message for isolation check",
        llm_processed=False
    )
    
    # Check that we only have our test message in the database
    from src.db.models.whatsapp_message import WhatsAppMessage
    all_messages = test_db.session.query(WhatsAppMessage).all()
    print(f"Total messages in test database: {len(all_messages)}")
    
    # Should only have our test message
    assert len(all_messages) == 1
    assert all_messages[0].id == message.id
    print("✓ Database isolation works - only test message exists")


def test_classify_messages_hang_check(classifier_with_test_db, test_data_factory):
    """Test if classify_messages() hangs."""
    classifier, test_db, mock_llm = classifier_with_test_db
    
    # Create test data
    user = test_data_factory.create_test_user(test_db.session)
    group = test_data_factory.create_test_group(test_db.session)
    message = test_data_factory.create_test_message(
        test_db.session,
        sender_id=user.id,
        group_id=group.id,
        raw_text="Test message for classification",
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
    
    print("About to call classify_messages()...")
    # This is where it might hang
    classifier.classify_messages()
    print("✓ classify_messages() completed successfully") 