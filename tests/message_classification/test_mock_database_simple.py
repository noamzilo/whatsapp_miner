#!/usr/bin/env python3
"""
Simple Mock Database Tests

Tests that demonstrate how to use the mock database for testing database operations.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path for proper imports
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestMockDatabaseSimple:
    """Tests demonstrating mock database usage without importing MessageClassifier."""

    def test_mock_db_session_basic(self, mock_db_session):
        """Test basic mock database session operations."""
        # The mock_db_session fixture provides a mocked database session
        # that can be used to test database operations without a real database
        
        # Test that we can call database methods
        mock_db_session.query.assert_not_called()
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()
        
        # Simulate some database operations
        mock_db_session.add("some_object")
        mock_db_session.commit()
        
        # Verify the methods were called
        mock_db_session.add.assert_called_once_with("some_object")
        mock_db_session.commit.assert_called_once()

    def test_mock_db_with_data(self, mock_db_with_data):
        """Test mock database with pre-populated test data."""
        # This fixture provides a mock database with some test data already set up
        
        # Test that we can query the mock database
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = Mock(
            template_name="lead_classification",
            prompt_text="Test classification prompt"
        )
        mock_db_with_data.query.return_value = mock_query
        
        # Simulate querying for a prompt
        result = mock_db_with_data.query("LeadClassificationPrompt").filter().first()
        
        # Verify the mock returned the expected data
        assert result is not None
        assert result.template_name == "lead_classification"
        assert result.prompt_text == "Test classification prompt"

    def test_database_operation_tracking(self, mock_db_session):
        """Test that we can track database operations."""
        # Create a test object
        test_object = Mock()
        test_object.id = "test_id"
        test_object.name = "test_name"
        
        # Simulate database operations
        mock_db_session.add(test_object)
        mock_db_session.commit()
        
        # Verify operations were tracked
        mock_db_session.add.assert_called_once_with(test_object)
        mock_db_session.commit.assert_called_once()
        
        # Test query operations
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = test_object
        mock_db_session.query.return_value = mock_query
        
        # Simulate a query
        result = mock_db_session.query("SomeModel").filter().first()
        
        # Verify the query was executed
        mock_db_session.query.assert_called_with("SomeModel")
        assert result == test_object

    def test_mock_db_error_handling(self, mock_db_session):
        """Test how mock database handles errors."""
        # Simulate a database error
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Test that the error is raised
        with pytest.raises(Exception, match="Database error"):
            mock_db_session.commit()
        
        # Verify the error was called
        mock_db_session.commit.assert_called_once()

    def test_mock_db_query_chaining(self, mock_db_session):
        """Test chaining database queries with mock."""
        # Set up mock query chain
        mock_filter = Mock()
        mock_filter.first.return_value = "test_result"
        mock_query = Mock()
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        # Execute chained query
        result = mock_db_session.query("TestModel").filter().first()
        
        # Verify the chain was executed correctly
        mock_db_session.query.assert_called_with("TestModel")
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()
        assert result == "test_result"

    def test_mock_db_session_context_manager(self, mock_db_session):
        """Test that mock database session works as a context manager."""
        # The mock should support context manager operations
        # This simulates how the real database session would be used
        
        # Test context manager behavior
        with mock_db_session as session:
            session.add("test_object")
            session.commit()
        
        # Verify the context manager methods were called
        mock_db_session.__enter__.assert_called_once()
        mock_db_session.__exit__.assert_called_once()
        mock_db_session.add.assert_called_once_with("test_object")
        mock_db_session.commit.assert_called_once()

    def test_mock_db_bulk_operations(self, mock_db_session):
        """Test bulk database operations with mock."""
        # Test adding multiple objects
        objects = [Mock(id=f"obj_{i}") for i in range(3)]
        
        for obj in objects:
            mock_db_session.add(obj)
        mock_db_session.commit()
        
        # Verify all adds were called
        assert mock_db_session.add.call_count == 3
        mock_db_session.commit.assert_called_once()
        
        # Test bulk query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = objects
        mock_db_session.query.return_value = mock_query
        
        # Simulate bulk query
        results = mock_db_session.query("TestModel").filter().all()
        
        # Verify bulk query
        assert len(results) == 3
        mock_db_session.query.assert_called_with("TestModel") 