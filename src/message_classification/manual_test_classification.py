#!/usr/bin/env python3
"""
MANUAL TEST: Full MessageClassifier Test

This is a manual test file to verify the MessageClassifier works with Groq API.
This test REQUIRES environment variables to be set.

PREREQUISITES:
1. Set GROQ_API_KEY environment variable
2. Set database connection variables (SUPABASE_DATABASE_CONNECTION_STRING, etc.)
3. Ensure database is accessible

USAGE OPTIONS:

Option 1: Using Doppler (Recommended)
    doppler run -- python src/message_classification/manual_test_classifier.py

Option 2: Manual Environment Variables
    export GROQ_API_KEY="your_groq_api_key_here"
    export SUPABASE_DATABASE_CONNECTION_STRING="your_db_connection_string"
    python src/message_classification/manual_test_classifier.py

This test will:
- Initialize the MessageClassifier
- Test classification with a sample message
- Verify LLM integration works
"""
import os

# Print all environment variables
for variable_name, value in os.environ.items():
	print(f"{variable_name} = {value}")

print(os.getcwd())
import logging
from src.message_classification.message_classifier import MessageClassifier

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_classifier():
	"""Test the message classifier with a sample message."""
	logger.info("🧪 Testing MessageClassifier")

	try:
		classifier = MessageClassifier()
		logger.info("✅ MessageClassifier initialized successfully")

		# Test with a sample message
		sample_message = "Hi everyone! I'm looking for a good dentist in the area. Any recommendations?"

		logger.info(f"📝 Testing classification with message: {sample_message}")

		result = classifier._classify_message(sample_message)

		logger.info(f"✅ Classification result: {result}")

		# Test with another message
		sample_message2 = "Just checking in to see how everyone is doing today!"

		logger.info(f"📝 Testing classification with second message: {sample_message2}")

		result2 = classifier._classify_message(sample_message2)

		logger.info(f"✅ Second classification result: {result2}")

		return True

	except Exception as e:
		logger.error(f"❌ Test failed: {e}")
		return False


if __name__ == "__main__":
	print("🧪 Running manual test for MessageClassifier...")
	print("📝 This test verifies the full classification pipeline works")
	print("🔧 REQUIRES: GROQ_API_KEY and database connection")
	print("⚠️  Make sure environment variables are set before running!")
	print("")
	print("SETUP INSTRUCTIONS:")
	print("")
	print("Option 1: Using Doppler (Recommended)")
	print("1. Install Doppler CLI: https://docs.doppler.com/docs/install-cli")
	print("2. Configure your Doppler project and secrets")
	print("3. Run: doppler run -- python src/message_classification/manual_test_classifier.py")
	print("")
	print("Option 2: Manual Environment Variables")
	print("1. Get a Groq API key from https://console.groq.com/")
	print("2. Set environment variables:")
	print("   export GROQ_API_KEY='your_api_key_here'")
	print("   export SUPABASE_DATABASE_CONNECTION_STRING='your_db_string'")
	print("3. Run: python src/message_classification/manual_test_classifier.py")
	print("-" * 50)

	success = test_classifier()

	print("-" * 50)
	if success:
		print("🎉 Manual test passed!")
		print("✅ The MessageClassifier is working correctly with Groq API")
	else:
		print("💥 Manual test failed!")
		print("❌ Check your environment variables and database connection")
		print("💡 Make sure you have set GROQ_API_KEY and database connection variables")
		print("💡 Or use Doppler: doppler run -- python src/message_classification/manual_test_classifier.py")
		exit(1)