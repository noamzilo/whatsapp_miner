#!/usr/bin/env python3
"""
Shared test fixtures and configuration.

This file contains pytest fixtures that can be used across all test files.
Organized for incremental testing from small to large blocks.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Generator

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.message_classification.message_classifier import ClassificationResult
from src.db.test_db import TestDatabase, TestDataFactory, SAMPLE_MESSAGES


# ============================================================================
# Level 1: Basic Mocking Fixtures (for testing classifier contract)
# ============================================================================

@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict('os.environ', {
        'MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS': '30',
        'GROQ_API_KEY': 'test_key'
    }):
        yield


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
        mock_llm = Mock()
        mock_chat_groq.return_value = mock_llm
        yield mock_llm


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    with patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
        mock_db = Mock()
        
        # Mock common database operations
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Set up context manager properly
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=None)
        
        mock_get_session.return_value.__enter__.return_value = mock_db
        mock_get_session.return_value.__exit__.return_value = None
        yield mock_db


@pytest.fixture
def mock_classifier(mock_llm, mock_db_session):
    """Create a MessageClassifier with mocked dependencies."""
    # Mock the prompt query with a realistic prompt
    mock_prompt = Mock()
    mock_prompt.prompt_text = "Analyze if this message is a lead. A lead is someone looking for a service or product. Respond with JSON containing is_lead (boolean), lead_category (string or null), lead_description (string or null), confidence_score (float), and reasoning (string)."
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_prompt
    
    from src.message_classification.message_classifier import MessageClassifier
    classifier = MessageClassifier()
    return classifier


# ============================================================================
# Level 2: Sample Data Fixtures (for testing classifier logic)
# ============================================================================

@pytest.fixture
def sample_classification_result():
    """Sample ClassificationResult for testing."""
    return ClassificationResult(
        is_lead=True,
        lead_category="dentist",
        lead_description="Looking for a dentist",
        confidence_score=0.9,
        reasoning="Message clearly asks for dentist recommendations"
    )


@pytest.fixture
def sample_non_lead_classification_result():
    """Sample non-lead ClassificationResult for testing."""
    return ClassificationResult(
        is_lead=False,
        lead_category=None,
        lead_description=None,
        confidence_score=0.8,
        reasoning="This is just a general conversation message"
    )


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return SAMPLE_MESSAGES


# ============================================================================
# Level 3: Test Database Fixtures (for testing with real database)
# ============================================================================

@pytest.fixture(scope="function")
def test_db():
    """Test database with proper setup and teardown."""
    db = TestDatabase()
    db.setup()
    yield db
    db.teardown()


@pytest.fixture
def test_data_factory():
    """Test data factory for creating test data."""
    return TestDataFactory()


@pytest.fixture
def test_session(test_db):
    """Get a test database session."""
    with test_db.get_session() as session:
        yield session


@pytest.fixture
def test_user(test_session, test_data_factory):
    """Create a test user."""
    return test_data_factory.create_test_user(test_session)


@pytest.fixture
def test_group(test_session, test_data_factory):
    """Create a test group."""
    return test_data_factory.create_test_group(test_session)


@pytest.fixture
def test_message(test_session, test_data_factory, test_user, test_group):
    """Create a test message."""
    return test_data_factory.create_test_message(
        test_session,
        sender_id=test_user.id,
        group_id=test_group.id
    )


# ============================================================================
# Level 4: Integration Test Fixtures (for full integration testing)
# ============================================================================

@pytest.fixture
def classifier_with_test_db(test_db, mock_llm):
    """Create a MessageClassifier with test database."""
    # Mock the database session to use test database
    with patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
        # Create a context manager that returns the test session
        class TestSessionContext:
            def __enter__(self):
                return test_db.session
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        mock_get_session.return_value = TestSessionContext()
        
        # Create a default prompt in the test database if it doesn't exist
        from src.db.models.lead_classification_prompt import LeadClassificationPrompt
        existing_prompt = test_db.session.query(LeadClassificationPrompt).filter(
            LeadClassificationPrompt.template_name == "lead_classification"
        ).first()
        
        if not existing_prompt:
            default_prompt = LeadClassificationPrompt(
                template_name="lead_classification",
                prompt_text="Analyze if this message is a lead. A lead is someone looking for a service or product. Respond with JSON containing is_lead (boolean), lead_category (string or null), lead_description (string or null), confidence_score (float), and reasoning (string).",
                version="1.0"
            )
            test_db.session.add(default_prompt)
            test_db.session.commit()
        
        from src.message_classification.message_classifier import MessageClassifier
        classifier = MessageClassifier()
        return classifier, test_db, mock_llm


@pytest.fixture
def sample_llm_responses():
    """Sample LLM responses for different message types."""
    return {
        "lead_dentist": {
            "content": '''{
                "is_lead": true,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message clearly asks for dentist recommendations"
            }'''
        },
        "lead_plumber": {
            "content": '''{
                "is_lead": true,
                "lead_category": "plumber",
                "lead_description": "Looking for a plumber",
                "confidence_score": 0.95,
                "reasoning": "Message urgently asks for plumber recommendations"
            }'''
        },
        "non_lead_greeting": {
            "content": '''{
                "is_lead": false,
                "lead_category": null,
                "lead_description": null,
                "confidence_score": 0.8,
                "reasoning": "This is just a general conversation message"
            }'''
        }
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root path."""
    return project_root


@pytest.fixture
def mock_groq_api_key():
    """Mock Groq API key."""
    with patch('src.message_classification.message_classifier.groq_api_key', 'test_key'):
        yield 