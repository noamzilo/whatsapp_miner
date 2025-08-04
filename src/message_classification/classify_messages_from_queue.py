#!/usr/bin/env python3
"""
Event-Driven Message Classifier Service
Consumes messages from Redis Streams queue for classification.

USAGE OPTIONS:

Option 1: Using Doppler (Recommended)
    doppler run -- python src/message_classification/classify_messages_from_queue.py

Option 2: Manual Environment Variables
    export GROQ_API_KEY="your_groq_api_key_here"
    export SUPABASE_DATABASE_CONNECTION_STRING="your_db_connection_string"
    export DATABASE_ENV="dev"  # or "prd"
    python src/message_classification/classify_messages_from_queue.py

The service runs continuously, consuming messages from Redis Streams as they arrive
(event-driven, no polling). Each consumer processes messages for its own environment.
"""
import os
import signal
import sys
import json
import logging
from typing import Dict, Any
from datetime import datetime

from src.utils.log import get_logger, setup_logger
from src.paths import logs_root
from src.message_queue.redis_streams_queue import RedisStreamsQueue
from src.message_classification.message_classifier import MessageClassifier
from src.db.db_interface import get_db_session

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


class QueueMessageClassifier:
    """Event-driven classifier service using Redis Streams."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.queue = RedisStreamsQueue()
        self.classifier = MessageClassifier()
        self.running = True
        
        # Consumer identification
        self.group_name = f"classifier_group_{environment}"
        self.consumer_name = f"classifier_{environment}_{os.getpid()}"
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"🤖 Initialized QueueMessageClassifier for environment '{environment}'")
        logger.info(f"👥 Consumer group: '{self.group_name}', Consumer: '{self.consumer_name}'")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def process_message(self, message_data: Dict[str, Any], environment: str) -> None:
        """Process a single message from the queue."""
        start_time = datetime.now()
        message_id = message_data.get('id', 'unknown')
        
        logger.info(f"📨 Processing message {message_id} for environment '{environment}'")
        
        try:
            with get_db_session() as session:
                # Classify the message
                classification_results = self.classifier.classify_messages([message_data], session)
                
                if classification_results and classification_results[0]['success']:
                    result = classification_results[0]['classification_result']
                    
                    # Log detailed classification
                    self._log_classification_result(message_data, result, environment)
                    
                    # Process results
                    processed_count = self.classifier.process_classification_results(classification_results, session)
                    
                    duration = (datetime.now() - start_time).total_seconds()
                    logger.info(f"✅ Processed message {message_id} in {duration:.2f}s for environment '{environment}'")
                    
                else:
                    logger.error(f"❌ Failed to classify message {message_id} for environment '{environment}'")
                    
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Error processing message {message_id} for environment '{environment}' in {duration:.2f}s: {e}")
    
    def _log_classification_result(self, message_data: Dict[str, Any], result: Any, environment: str) -> None:
        """Log detailed classification results."""
        message_id = message_data.get('id', 'unknown')
        message_text = message_data.get('raw_text', '')
        sender_id = message_data.get('sender_id', 'unknown')
        group_id = message_data.get('group_id', 'unknown')
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "environment": environment,
            "message_id": message_id,
            "sender_id": sender_id,
            "group_id": group_id,
            "message_text": message_text,
            "message_length": len(message_text),
            "classification": {
                "is_lead": result.is_lead,
                "lead_category": result.lead_category,
                "lead_description": result.lead_description,
                "reasoning": result.reasoning
            }
        }
        
        if result.is_lead:
            logger.info(f"🎯 LEAD DETECTED [{environment}] - Message {message_id} | Category: '{result.lead_category}' | Description: '{result.lead_description}'")
            logger.info(f"📝 FULL MESSAGE TEXT [{environment}]: {message_text}")
        else:
            logger.info(f"📝 NON-LEAD [{environment}] - Message {message_id} | Reasoning: {result.reasoning}")
            logger.info(f"📝 FULL MESSAGE TEXT [{environment}]: {message_text}")
        
        # Log structured data
        logger.info(f"📋 DETAILED CLASSIFICATION LOG [{environment}]: {json.dumps(log_entry, indent=2, default=str)}")
    
    def run(self):
        """Run the event-driven classifier service."""
        try:
            # Create consumer group
            self.queue.create_consumer_group(self.group_name, self.consumer_name)
            
            logger.info(f"🎧 Starting streams classifier for environment '{self.environment}'")
            
            # Consume messages with acknowledgment
            self.queue.consume_messages(
                group_name=self.group_name,
                consumer_name=self.consumer_name,
                processor_func=self.process_message,
                environment=self.environment
            )
            
        except KeyboardInterrupt:
            logger.info(f"🛑 Service stopped by user for environment '{self.environment}'")
        except Exception as e:
            logger.error(f"❌ Service error for environment '{self.environment}': {e}")
            raise


def main():
    """Main entry point for queue classifier service."""
    # Get environment from environment variable
    environment = os.environ.get('DATABASE_ENV', 'dev')
    
    logger.info(f"🤖 Starting Queue Classifier Service for environment '{environment}'")
    
    service = QueueMessageClassifier(environment)
    
    try:
        service.run()
    except Exception as e:
        logger.error(f"❌ Queue Classifier Service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 