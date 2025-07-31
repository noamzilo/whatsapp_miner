#!/usr/bin/env python3
"""
Message Classifier Service
Runs in a continuous loop to classify new messages.
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