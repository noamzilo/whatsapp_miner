#!/usr/bin/env python3
"""
Shared test fixtures and configuration.

This file contains pytest fixtures that can be used across all test files.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root path."""
    return project_root


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict('os.environ', {
        'MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS': '30'
    }):
        yield


@pytest.fixture
def sample_classification_result():
    """Sample ClassificationResult for testing."""
    from src.message_classification.message_classifier import ClassificationResult
    
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
    from src.message_classification.message_classifier import ClassificationResult
    
    return ClassificationResult(
        is_lead=False,
        lead_category=None,
        lead_description=None,
        confidence_score=0.8,
        reasoning="This is just a general conversation message"
    )


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    with patch('src.message_classification.message_classifier.get_db_session') as mock_session:
        mock_db = Mock()
        
        # Mock common database operations
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mock_session.return_value.__enter__.return_value = mock_db
        mock_session.return_value.__exit__.return_value = None
        yield mock_db


@pytest.fixture
def mock_db_with_data():
    """Mock database session with pre-populated test data."""
    with patch('src.message_classification.message_classifier.get_db_session') as mock_session:
        mock_db = Mock()
        
        # Create mock objects for test data
        mock_prompt = Mock()
        mock_prompt.id = 1
        mock_prompt.template_name = "lead_classification"
        mock_prompt.prompt_text = "Test classification prompt"
        
        mock_intent_type = Mock()
        mock_intent_type.id = 1
        mock_intent_type.name = "lead_seeking"
        
        mock_category = Mock()
        mock_category.id = 1
        mock_category.name = "dentist"
        
        # Mock query responses
        def mock_query_response(model_class):
            mock_query = Mock()
            if model_class.__name__ == "LeadClassificationPrompt":
                mock_query.filter.return_value.first.return_value = mock_prompt
            elif model_class.__name__ == "MessageIntentType":
                mock_query.filter.return_value.first.return_value = mock_intent_type
            elif model_class.__name__ == "LeadCategory":
                mock_query.filter.return_value.first.return_value = mock_category
            else:
                mock_query.filter.return_value.first.return_value = None
                mock_query.filter.return_value.all.return_value = []
            return mock_query
        
        mock_db.query.side_effect = mock_query_response
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        mock_session.return_value.__enter__.return_value = mock_db
        mock_session.return_value.__exit__.return_value = None
        yield mock_db 