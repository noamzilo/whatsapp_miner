# Tests

This directory contains the test suite for the WhatsApp Miner project.

## Test Structure

```
tests/
├── conftest.py                           # Shared test fixtures
├── message_classification/
│   ├── test_classification_result.py     # Tests for ClassificationResult model
│   ├── test_message_classifier.py        # Tests for MessageClassifier (requires env vars)
│   └── test_message_classifier_simple.py # Simple tests that don't require env vars
└── README.md                             # This file
```

## Running Tests

### Prerequisites

1. Install dev dependencies:
   ```bash
   poetry install --with dev
   ```

2. Make sure you're in the project root directory.

### Running All Tests

```bash
# Run all tests
poetry run pytest tests/ -v

# Run with coverage (if pytest-cov is installed)
poetry run pytest tests/ -v --cov=src
```

### Running Specific Test Files

```bash
# Run only ClassificationResult tests
poetry run pytest tests/message_classification/test_classification_result.py -v

# Run simple MessageClassifier tests (no env vars required)
poetry run pytest tests/message_classification/test_message_classifier_simple.py -v

# Run all message classification tests
poetry run pytest tests/message_classification/ -v
```

### Using the Test Runner Script

```bash
# Run tests using the provided script
./run_tests.sh
```

## Test Categories

### 1. ClassificationResult Tests (`test_classification_result.py`)

Tests for the Pydantic model used for structured LLM classification output:

- ✅ Model creation and validation
- ✅ JSON serialization
- ✅ Edge cases (min/max confidence scores)
- ✅ Optional field handling
- ✅ Model dumping to dict/JSON

### 2. Simple MessageClassifier Tests (`test_message_classifier_simple.py`)

Tests that don't require environment variables or external dependencies:

- ✅ ClassificationResult structure validation
- ✅ Input validation
- ✅ JSON serialization
- ✅ Edge cases
- ✅ Parametrized tests

### 3. Full MessageClassifier Tests (`test_message_classifier.py`)

**Note: These tests require environment variables to be set.**

Tests for the complete MessageClassifier with mocked dependencies:

- ✅ Classifier initialization
- ✅ Message classification (lead vs non-lead)
- ✅ Error handling
- ✅ Invalid JSON response handling
- ✅ Retry logic
- ✅ Various message types

### 4. Database Testing Explanation (`test_database_explanation.py`)

Educational tests that explain different database testing approaches:

- ✅ Mock database testing (unit tests)
- ✅ In-memory SQLite testing (integration tests)
- ✅ Test database testing (end-to-end tests)
- ✅ Database fixtures and best practices
- ✅ End-to-end database test examples

### 5. Integration Tests (`test_message_classifier_integration.py`)

**Note: These tests require environment variables and database setup.**

Full end-to-end tests using real in-memory SQLite database:

- ✅ Complete message classification flow
- ✅ Database record creation and verification
- ✅ Lead detection and storage
- ✅ Multiple message processing
- ✅ Real database operations

## Environment Variables

Some tests require environment variables to be set. For tests that need them:

```bash
# Option 1: Using Doppler (Recommended)
doppler run -- poetry run pytest tests/message_classification/test_message_classifier.py -v

# Option 2: Manual environment variables
export GROQ_API_KEY="your_groq_api_key"
export SUPABASE_DATABASE_CONNECTION_STRING="your_db_connection_string"
poetry run pytest tests/message_classification/test_message_classifier.py -v
```

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `project_root_path`: Returns the project root path
- `mock_env_vars`: Mocks environment variables for testing
- `sample_classification_result`: Sample lead classification result
- `sample_non_lead_classification_result`: Sample non-lead classification result
- `mock_db_session`: Mock database session
- `mock_db_with_data`: Mock database session with pre-populated test data

## Database Testing Approaches

### 1. Mock Database Testing (Unit Tests)
```python
# Fast, no real database needed
mock_db = Mock()
mock_db.add.return_value = None
mock_db.commit.return_value = None

# Test business logic without database dependencies
classifier.process_message(mock_db)
mock_db.add.assert_called_once()
```

### 2. In-Memory SQLite Testing (Integration Tests)
```python
# Real database operations, but in memory
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

# Test actual database operations
message = WhatsAppMessage(raw_text="Looking for dentist")
session.add(message)
session.commit()
```

### 3. Test Database Testing (End-to-End Tests)
```python
# Real PostgreSQL/MySQL database for testing
TEST_DB_URL = "postgresql://user:pass@localhost/test_db"
engine = create_engine(TEST_DB_URL)

# Test with production-like database
# Run migrations, test complex queries
```

### 4. Database Fixtures
```python
@pytest.fixture
def test_db_session():
    # Set up database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    
    try:
        yield session
    finally:
        session.close()
```

## Adding New Tests

1. Create test files following the naming convention: `test_*.py`
2. Use descriptive test class and method names
3. Add proper docstrings to test methods
4. Use the shared fixtures from `conftest.py` when possible
5. Mock external dependencies to avoid requiring real API keys or database connections

## Test Coverage

The tests cover:

- ✅ Pydantic model validation
- ✅ JSON serialization/deserialization
- ✅ Error handling and edge cases
- ✅ Mocked LLM interactions
- ✅ Database session mocking
- ✅ Environment variable handling

## Troubleshooting

### Import Errors

If you get import errors, make sure:
1. You're running tests from the project root
2. Dev dependencies are installed: `poetry install --with dev`
3. The virtual environment is activated

### Environment Variable Errors

If tests fail due to missing environment variables:
1. Use the simple tests that don't require env vars
2. Set up environment variables using Doppler or manual export
3. Use the mocked tests that don't require real API keys

### Database Connection Errors

The tests use mocked database sessions, so they shouldn't require real database connections. If you get database errors, check that the mocking is working correctly. 