#!/usr/bin/env python3
"""
Message Classifier Service
Runs in a continuous loop to classify new messages.

USAGE OPTIONS:

Option 1: Using Doppler (Recommended)
    doppler run -- python src/message_classification/classify_new_messages.py

Option 2: Manual Environment Variables
    export GROQ_API_KEY="your_groq_api_key_here"
    export SUPABASE_DATABASE_CONNECTION_STRING="your_db_connection_string"
    export MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS="30"
    python src/message_classification/classify_new_messages.py

The service will run continuously, checking for new messages every X seconds
(configurable via MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS environment variable).
"""

import logging
from src.message_classification.message_classifier import MessageClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function that runs the message classifier in a loop."""
    logger.info("🚀 Starting Message Classifier Service")
    
    classifier = MessageClassifier()
    
    try:
        classifier.run_continuous()
    except KeyboardInterrupt:
        logger.info("🛑 Message Classifier Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Message Classifier Service error: {e}")
        raise

if __name__ == "__main__":
    main() 