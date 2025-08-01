# Hanging Test Debug Guide

## Problem Summary

The `test_04_full_integration.py` tests were hanging due to several issues:

1. **Real LLM API Calls**: The `MessageClassifier` was being initialized with a real `ChatGroq` instance, which could make real API calls even when mocked later.

2. **Missing Timeouts**: No timeouts were in place to prevent infinite hanging.

3. **Mock Not Applied**: The mock LLM wasn't properly applied to the classifier instance.

4. **Database Session Issues**: Potential transaction issues with the test database.

## Fixes Applied

### 1. Fixed Test Fixture (`tests/conftest.py`)

**Problem**: The `classifier_with_test_db` fixture was creating a real `ChatGroq` instance.

**Fix**: Added proper mocking of the `ChatGroq` initialization:

```python
# Mock the LLM initialization to prevent real API calls
with patch('src.message_classification.message_classifier.ChatGroq') as mock_chat_groq:
    mock_chat_groq.return_value = mock_llm
    
    from src.message_classification.message_classifier import MessageClassifier
    classifier = MessageClassifier()
    
    # Ensure the mock LLM is set on the classifier
    classifier.llm = mock_llm
    
    return classifier, test_db, mock_llm
```

### 2. Added Timeout Protection (`tests/message_classification/test_04_full_integration.py`)

**Problem**: No timeouts to prevent infinite hanging.

**Fix**: Added timeout context manager and wrapped all classification calls:

```python
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

# Usage in tests:
try:
    with timeout_context(30):  # 30 second timeout
        classifier.classify_messages()
except TimeoutError:
    pytest.fail("Test timed out - likely hanging on LLM call or database operation")
```

### 3. Ensured Mock Application

**Problem**: Mock LLM wasn't properly applied to the classifier.

**Fix**: Explicitly set the mock on the classifier instance:

```python
# Ensure the mock is applied to the classifier's LLM instance
classifier.llm = mock_llm
```

### 4. Implemented All Test Cases

**Problem**: Most tests were just `pass` statements.

**Fix**: Implemented comprehensive test cases for:
- Lead message classification
- Non-lead message classification  
- Multiple messages classification
- Existing categories reuse
- Error handling

## Debug Tools Created

### 1. Debug Test File (`tests/message_classification/test_debug_hanging.py`)

Step-by-step debug tests to identify exact hanging points:
- `test_debug_classifier_initialization`
- `test_debug_database_operations`
- `test_debug_llm_mocking`
- `test_debug_full_classification_step_by_step`
- `test_debug_classify_messages_method`

### 2. Debug Test Runner (`tests/message_classification/run_debug_tests.py`)

Standalone script to run specific debug tests with timeouts:

```bash
# Test classifier initialization
python tests/message_classification/run_debug_tests.py classifier_init

# Test database operations
python tests/message_classification/run_debug_tests.py database_ops

# Test LLM classification
python tests/message_classification/run_debug_tests.py llm_classification

# Test full classification flow
python tests/message_classification/run_debug_tests.py full_classification
```

## How to Debug Hanging Issues

### 1. Run Individual Debug Tests

```bash
# Run with pytest (with timeout)
pytest tests/message_classification/test_debug_hanging.py::TestDebugHanging::test_debug_classifier_initialization -v -s

# Run with debug script
python tests/message_classification/run_debug_tests.py classifier_init 10
```

### 2. Check for Real API Calls

Look for these indicators of real API calls:
- Network activity in logs
- API key usage
- Slow responses (>5 seconds)

### 3. Verify Mock Application

Ensure the mock is properly applied:
```python
print(f"LLM type: {type(classifier.llm)}")
print(f"Is mock: {hasattr(classifier.llm, '_mock_name')}")
```

### 4. Check Database Operations

Verify database operations don't hang:
```python
# Test session creation
session = test_db.session
print("✅ Session created")

# Test simple query
result = session.query(SomeModel).first()
print("✅ Query successful")
```

## Prevention Measures

### 1. Always Use Timeouts

Wrap all potentially hanging operations:
```python
with timeout_context(30):
    classifier.classify_messages()
```

### 2. Verify Mocks

Always ensure mocks are properly applied:
```python
classifier.llm = mock_llm
```

### 3. Test with Minimal Data

Use small datasets for integration tests:
```python
# Create only necessary test data
user = test_data_factory.create_test_user(test_db.session)
group = test_data_factory.create_test_group(test_db.session)
message = test_data_factory.create_test_message(
    test_db.session,
    sender_id=user.id,
    group_id=group.id,
    raw_text="Test message",
    llm_processed=False
)
```

### 4. Use Debug Logging

Add debug prints to identify hanging points:
```python
print("🔍 Step 1: Getting unclassified messages...")
unclassified = classifier._get_unclassified_messages(session)
print(f"✅ Found {len(unclassified)} unclassified messages")
```

## Running the Fixed Tests

### Run All Integration Tests
```bash
pytest tests/message_classification/test_04_full_integration.py -v -s
```

### Run Individual Tests
```bash
# Test lead message classification
pytest tests/message_classification/test_04_full_integration.py::TestFullIntegration::test_full_classification_flow_lead_message -v -s

# Test non-lead message classification
pytest tests/message_classification/test_04_full_integration.py::TestFullIntegration::test_full_classification_flow_non_lead_message -v -s
```

### Run with Debug Output
```bash
pytest tests/message_classification/test_04_full_integration.py -v -s --tb=short
```

## Expected Behavior

After the fixes:
1. Tests should complete within 30 seconds
2. No real API calls should be made
3. All database operations should succeed
4. Mock responses should be used for LLM calls
5. Proper error handling should prevent crashes

If tests still hang, use the debug tools to identify the exact hanging point. 