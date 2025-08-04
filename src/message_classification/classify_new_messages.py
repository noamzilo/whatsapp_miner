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
import time
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

from src.paths import logs_root
from src.utils.log import get_logger, setup_logger
from src.message_classification.message_classifier import MessageClassifier
from src.db.db_interface import get_db_session
from src.db.db import (
    get_unclassified_messages, mark_message_as_processed, create_classification_record,
    create_lead_record, get_or_create_lead_category, get_or_create_intent_type,
    get_classification_prompt, match_with_existing_categories
)

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


class MessageClassifierService:
    """Production service for classifying new messages."""
    
    def __init__(self):
        """Initialize the message classifier service."""
        self.classifier = MessageClassifier()
        logger.info("✅ Initialized MessageClassifierService")
    
    def _create_detailed_message_log(self, message_data: Dict[str, Any], classification_result: Any, 
                                   processing_stats: Dict[str, Any]) -> None:
        """Create a detailed log entry for each classified message."""
        try:
            # Extract message details
            message_id = message_data['id']
            message_text = message_data['raw_text']
            sender_id = message_data.get('sender_id')
            group_id = message_data.get('group_id')
            timestamp = message_data.get('timestamp')
            
            # Extract classification details
            is_lead = classification_result.is_lead
            lead_category = classification_result.lead_category
            lead_description = classification_result.lead_description
            reasoning = classification_result.reasoning
            
            # Create detailed log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "message_id": message_id,
                "sender_id": sender_id,
                "group_id": group_id,
                "message_timestamp": timestamp.isoformat() if timestamp else None,
                "message_text": message_text,
                "message_length": len(message_text),
                "classification": {
                    "is_lead": is_lead,
                    "lead_category": lead_category,
                    "lead_description": lead_description,
                    "reasoning": reasoning
                },
                "processing_stats": processing_stats
            }
            
            # Log the detailed entry
            logger.info(f"📋 DETAILED CLASSIFICATION LOG: {json.dumps(log_entry, indent=2, default=str)}")
            
            # Also log a concise summary
            if is_lead:
                logger.info(f"🎯 LEAD DETECTED - Message {message_id}: Category='{lead_category}', Description='{lead_description}'")
            else:
                logger.info(f"📝 NON-LEAD - Message {message_id}: {reasoning[:100]}...")
                
        except Exception as e:
            logger.error(f"❌ Error creating detailed log for message {message_data.get('id', 'unknown')}: {e}")
    
    def _get_unclassified_messages(self, session, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unclassified messages from the database."""
        try:
            unclassified_messages = get_unclassified_messages(session)
            
            # Convert to dictionary format for classifier and filter short messages
            messages = []
            for msg in unclassified_messages[:limit]:
                # Skip messages under 8 characters
                if len(msg.raw_text.strip()) < 8:
                    logger.debug(f"⏭️  Skipping short message {msg.id}: '{msg.raw_text[:20]}...' (length: {len(msg.raw_text)})")
                    continue
                
                messages.append({
                    'id': msg.id,
                    'raw_text': msg.raw_text,
                    'sender_id': msg.sender_id,
                    'group_id': msg.group_id,
                    'timestamp': msg.timestamp
                })
            
            logger.info(f"📖 Found {len(messages)} unclassified messages (after filtering short messages)")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting unclassified messages: {e}")
            return []
    
    def _process_classification_results(self, classification_results: List[Dict[str, Any]], session) -> int:
        """Process classification results and update database."""
        # Use the centralized classification logic from MessageClassifier
        return self.classifier.process_classification_results(classification_results, session)
    
    def _run_classification_iteration(self) -> Dict[str, Any]:
        """Run a single classification iteration."""
        start_time = datetime.now()
        iteration_stats = {
            'messages_found': 0,
            'messages_processed': 0,
            'leads_detected': 0,
            'errors': 0,
            'duration_seconds': 0
        }
        
        try:
            with get_db_session() as session:
                # Get unclassified messages
                messages = self._get_unclassified_messages(session)
                iteration_stats['messages_found'] = len(messages)
                
                if not messages:
                    logger.info("📭 No unclassified messages found")
                    return iteration_stats
                
                # Classify messages
                logger.info(f"🤖 Classifying {len(messages)} messages...")
                classification_results = self.classifier.classify_messages(messages, session)
                
                # Create detailed logs for each classified message
                for i, result in enumerate(classification_results):
                    if result['success']:
                        message_data = messages[i]  # Assuming same order
                        classification_result = result['classification_result']
                        
                        # Create processing stats for this message
                        processing_stats = {
                            'iteration_number': iteration_stats.get('iteration_number', 0),
                            'message_index': i + 1,
                            'total_messages_in_batch': len(messages),
                            'processing_timestamp': datetime.now().isoformat()
                        }
                        
                        # Create detailed log for this message
                        self._create_detailed_message_log(message_data, classification_result, processing_stats)
                        
                        # Update stats
                        if classification_result.is_lead:
                            iteration_stats['leads_detected'] += 1
                    else:
                        logger.error(f"❌ Failed to classify message {result.get('message_id', 'unknown')}: {result.get('error', 'Unknown error')}")
                        iteration_stats['errors'] += 1
                
                # Process results
                processed_count = self._process_classification_results(classification_results, session)
                iteration_stats['messages_processed'] = processed_count
                
                logger.info(f"✅ Processed {processed_count}/{len(messages)} messages, detected {iteration_stats['leads_detected']} leads")
                
        except Exception as e:
            logger.error(f"❌ Error in classification iteration: {e}")
            iteration_stats['errors'] = 1
        
        finally:
            iteration_stats['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        
        return iteration_stats
    
    def run_continuous(self):
        """Run the classifier in a continuous loop."""
        logger.info("🚀 Starting Message Classifier Service")
        logger.info(f"⏰ Running every {self.classifier.message_classifier_run_every_seconds} seconds")
        
        iteration = 0
        total_stats = {
            'total_iterations': 0,
            'total_messages_processed': 0,
            'total_leads_detected': 0,
            'total_errors': 0
        }
        
        while True:
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"🔄 Iteration {iteration} - {current_time}")
            
            try:
                # Run classification iteration
                iteration_stats = self._run_classification_iteration()
                iteration_stats['iteration_number'] = iteration
                
                # Update total stats
                total_stats['total_iterations'] += 1
                total_stats['total_messages_processed'] += iteration_stats['messages_processed']
                total_stats['total_leads_detected'] += iteration_stats['leads_detected']
                total_stats['total_errors'] += iteration_stats['errors']
                
                # Log iteration summary
                logger.info(f"📊 Iteration Summary: "
                          f"Processed {iteration_stats['messages_processed']} messages, "
                          f"Detected {iteration_stats['leads_detected']} leads, "
                          f"Duration: {iteration_stats['duration_seconds']:.2f}s")
                
                # Log cumulative stats every 10 iterations
                if iteration % 10 == 0:
                    logger.info(f"📈 Cumulative Stats: "
                              f"Total processed: {total_stats['total_messages_processed']}, "
                              f"Total leads: {total_stats['total_leads_detected']}, "
                              f"Total errors: {total_stats['total_errors']}")
                
            except KeyboardInterrupt:
                logger.info("🛑 Message Classifier Service stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Critical error in classification iteration: {e}")
                total_stats['total_errors'] += 1
                # Continue running despite errors
            
            # Sleep for the configured interval
            time.sleep(self.classifier.message_classifier_run_every_seconds)


def main():
    """Main function that runs the message classifier service."""
    logger.info("🤖 Starting Message Classifier Service")
    
    service = MessageClassifierService()
    
    try:
        service.run_continuous()
    except KeyboardInterrupt:
        logger.info("🛑 Message Classifier Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Message Classifier Service error: {e}")
        raise


if __name__ == "__main__":
    main() 