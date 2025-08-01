#!/usr/bin/env python3
"""
Debug Test Runner

This script runs specific debug tests to identify hanging issues.
"""

import sys
import os
import signal
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

def timeout_handler(signum, frame):
    """Handle timeout signal."""
    print(f"❌ Test timed out after {signum} seconds")
    sys.exit(1)

def run_debug_test(test_name: str, timeout_seconds: int = 30):
    """Run a specific debug test with timeout."""
    print(f"🔍 Running debug test: {test_name}")
    print(f"⏰ Timeout: {timeout_seconds} seconds")
    
    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        # Import and run the test
        if test_name == "classifier_init":
            # Create test database manually
            from src.db.test_db import TestDatabase
            test_db = TestDatabase()
            test_db.setup()
            
            # Create mock LLM
            mock_llm = Mock()
            
            # Mock the LLM initialization
            with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
                mock_chat_groq.return_value = mock_llm
                
                from src.message_classification.message_classifier import MessageClassifier
                classifier = MessageClassifier()
                classifier.llm = mock_llm
                
                print("✅ Classifier initialization successful")
                
                # Cleanup
                test_db.teardown()
            
        elif test_name == "database_ops":
            # Create test database manually
            from src.db.test_db import TestDatabase, TestDataFactory
            test_db = TestDatabase()
            test_db.setup()
            factory = TestDataFactory()
            
            # Test database operations
            user = factory.create_test_user(test_db.session)
            group = factory.create_test_group(test_db.session)
            message = factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="Test message",
                llm_processed=False
            )
            print("✅ Database operations successful")
            
            # Cleanup
            test_db.teardown()
            
        elif test_name == "llm_classification":
            # Create test database manually
            from src.db.test_db import TestDatabase
            test_db = TestDatabase()
            test_db.setup()
            
            # Create mock LLM
            mock_llm = Mock()
            
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
            
            # Mock the LLM initialization
            with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
                mock_chat_groq.return_value = mock_llm
                
                from src.message_classification.message_classifier import MessageClassifier
                classifier = MessageClassifier()
                classifier.llm = mock_llm
                
                # Test classification
                result = classifier._classify_message("Test message")
                print(f"✅ LLM classification successful: {result}")
                
                # Cleanup
                test_db.teardown()
            
        elif test_name == "full_classification":
            # Create test database manually
            from src.db.test_db import TestDatabase, TestDataFactory
            test_db = TestDatabase()
            test_db.setup()
            factory = TestDataFactory()
            
            # Create test data
            user = factory.create_test_user(test_db.session)
            group = factory.create_test_group(test_db.session)
            message = factory.create_test_message(
                test_db.session,
                sender_id=user.id,
                group_id=group.id,
                raw_text="Looking for a dentist",
                llm_processed=False
            )
            
            # Create mock LLM
            mock_llm = Mock()
            
            # Mock the response
            mock_response = Mock()
            mock_response.content = '''{
                "is_lead": true,
                "lead_category": "dentist",
                "lead_description": "Looking for a dentist",
                "confidence_score": 0.9,
                "reasoning": "Message asks for dentist recommendations"
            }'''
            mock_llm.invoke.return_value = mock_response
            
            # Mock the LLM initialization and database session
            with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq, \
                 patch('src.message_classification.message_classifier.get_db_session') as mock_get_session:
                
                mock_chat_groq.return_value = mock_llm
                
                # Create a context manager that returns the test session
                class TestSessionContext:
                    def __enter__(self):
                        return test_db.session
                    def __exit__(self, exc_type, exc_val, exc_tb):
                        pass
                
                mock_get_session.return_value = TestSessionContext()
                
                from src.message_classification.message_classifier import MessageClassifier
                classifier = MessageClassifier()
                classifier.llm = mock_llm
                
                # Run classification
                classifier.classify_messages()
                print("✅ Full classification successful")
                
                # Cleanup
                test_db.teardown()
            
        else:
            print(f"❌ Unknown test: {test_name}")
            return False
            
        # Clear timeout
        signal.alarm(0)
        print(f"✅ Test '{test_name}' completed successfully")
        return True
        
    except Exception as e:
        signal.alarm(0)
        print(f"❌ Test '{test_name}' failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run debug tests."""
    if len(sys.argv) < 2:
        print("Usage: python run_debug_tests.py <test_name> [timeout_seconds]")
        print("Available tests:")
        print("  classifier_init - Test classifier initialization")
        print("  database_ops - Test database operations")
        print("  llm_classification - Test LLM classification")
        print("  full_classification - Test full classification flow")
        return
    
    test_name = sys.argv[1]
    timeout_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    success = run_debug_test(test_name, timeout_seconds)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 