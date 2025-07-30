#!/usr/bin/env python3
"""
Message Classifier Service
Runs in a continuous loop to classify new messages.
"""

import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function that runs the message classifier in a loop."""
    logger.info("🚀 Starting Message Classifier Service")
    logger.info("📊 Service will log messages every 20 seconds")
    
    iteration = 0
    while True:
        iteration += 1
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"🔄 Iteration {iteration} - {current_time}")
        logger.info("📝 Message classifier is running... (placeholder for actual classification logic)")
        
        # Sleep for 20 seconds
        time.sleep(20)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Message Classifier Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Message Classifier Service error: {e}")
        raise 