# Message Classification Tests

This directory contains organized, incremental tests for the message classification system.

## Test Structure

The tests are organized in levels from small to large blocks:

### Level 1: Classifier Contract Tests (`test_01_classifier_contract.py`)
- **Purpose**: Test the MessageClassifier contract and interface with full mocking
- **Scope**: Smallest test blocks that verify basic functionality
- **Dependencies**: Mocked LLM and database
- **Speed**: Fast

**Tests include:**
- Classifier initialization
- ClassificationResult structure validation
- Required methods existence
- Database operation mocking
- Basic contract verification

### Level 2: Classifier Logic Tests (`test_02_classifier_logic.py`)
- **Purpose**: Test the MessageClassifier actual logic with real LLM calls (mocked responses)
- **Scope**: Medium test blocks that verify classification logic
- **Dependencies**: Mocked LLM responses, mocked database
- **Speed**: Slow (marked with `@pytest.mark.slow`)

**Tests include:**
- Real LLM classification (with mocked responses)
- Various message type classification
- Error handling and retry logic
- Confidence score validation
- JSON parsing and validation

### Level 3: Database Integration Tests (`test_03_database_integration.py`)
- **Purpose**: Test database integration with test database and mock messages
- **Scope**: Medium test blocks that verify database operations
- **Dependencies**: Test database with migrations, mocked LLM
- **Speed**: Medium

**Tests include:**
- Database setup and migrations
- Test data factory functionality
- Database session management
- Lead category and intent type creation
- Message processing and record creation
- Unclassified messages querying

### Level 4: Full Integration Tests (`test_04_full_integration.py`)
- **Purpose**: Test the complete message classification flow with real database and mocked LLM
- **Scope**: Largest test blocks that verify the entire system works together
- **Dependencies**: Test database, mocked LLM
- **Speed**: Slow

**Tests include:**
- Complete classification flow for lead messages
- Complete classification flow for non-lead messages
- Multiple messages classification
- Existing categories reuse
- Error handling in full flow

## Test Database

The test database is managed by `src/db/test_db.py` and provides:

- **TestDatabase**: In-memory SQLite database with proper setup/teardown
- **TestDataFactory**: Factory for creating test data
- **SAMPLE_MESSAGES**: Predefined test messages for different scenarios

## Running Tests

### Run all tests:
```bash
pytest tests/message_classification/
```

### Run only fast tests (exclude slow tests):
```bash
pytest tests/message_classification/ -m "not slow"
```

### Run only slow tests:
```bash
pytest tests/message_classification/ -m "slow"
```

### Run tests by level:
```bash
# Level 1: Contract tests
pytest tests/message_classification/test_01_classifier_contract.py

# Level 2: Logic tests
pytest tests/message_classification/test_02_classifier_logic.py

# Level 3: Database integration tests
pytest tests/message_classification/test_03_database_integration.py

# Level 4: Full integration tests
pytest tests/message_classification/test_04_full_integration.py
```

### Run with verbose output:
```bash
pytest tests/message_classification/ -v -s
```

## Manual Testing Script

For manual testing with the real database, use the script:

```bash
python src/scripts/classify_fake_message.py
```

This script allows you to:
- Select from predefined sample messages
- Enter custom messages
- Classify messages using the real classifier
- Add results to the real database
- View detailed classification results

## Test Fixtures

All test fixtures are defined in `tests/conftest.py` and organized by level:

- **Level 1**: Basic mocking fixtures (`mock_llm`, `mock_db_session`, `mock_classifier`)
- **Level 2**: Sample data fixtures (`sample_classification_result`, `sample_messages`)
- **Level 3**: Test database fixtures (`test_db`, `test_data_factory`, `test_session`)
- **Level 4**: Integration fixtures (`classifier_with_test_db`, `sample_llm_responses`)

## Best Practices

1. **Incremental Testing**: Start with Level 1 tests, then progress to higher levels
2. **Isolation**: Each test level can run independently
3. **Speed**: Level 1 tests are fast, Level 2+ tests are slower
4. **Mocking**: Use appropriate mocking for each level
5. **Database**: Use test database for Level 3+ tests
6. **Real Testing**: Use the manual script for real database testing

## Debugging

If tests are hanging or failing:

1. Check the test database setup in `src/db/test_db.py`
2. Verify LLM mocking is working correctly
3. Check database migrations are applied
4. Use the manual script for real database testing
5. Run tests with verbose output: `pytest -v -s` 