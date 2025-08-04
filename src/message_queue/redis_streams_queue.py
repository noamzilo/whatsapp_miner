import redis
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.utils.log import get_logger, setup_logger
from src.paths import logs_root

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


class RedisStreamsQueue:
    """Consumer-side queue using Redis Streams for reliable message delivery."""
    
    def __init__(self, host: str = 'redis', port: int = 6379):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        self.stream_name = 'whatsapp_messages'
        logger.info(f"🔌 Initialized Redis Streams queue on {host}:{port}")
    
    def publish_message(self, message_data: Dict[str, Any]) -> str:
        """Publish message to Redis stream (fire-and-forget)."""
        try:
            # Add metadata
            message_data['timestamp'] = datetime.now().isoformat()
            message_data['source'] = 'whatsapp_sniffer'
            
            # Add to stream (auto-generates ID)
            message_id = self.redis_client.xadd(
                self.stream_name,
                message_data
            )
            
            logger.info(f"📤 Published message {message_data.get('id', 'unknown')} to stream '{self.stream_name}' with ID {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"❌ Failed to publish message: {e}")
            raise
    
    def create_consumer_group(self, group_name: str, consumer_name: str) -> None:
        """Create consumer group for reliable message processing."""
        try:
            # Create consumer group (creates stream if doesn't exist)
            self.redis_client.xgroup_create(
                self.stream_name,
                group_name,
                id='0',  # Start from beginning
                mkstream=True  # Create stream if doesn't exist
            )
            logger.info(f"👥 Created consumer group '{group_name}' for stream '{self.stream_name}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"👥 Consumer group '{group_name}' already exists")
            else:
                raise
    
    def consume_messages(self, group_name: str, consumer_name: str, 
                        processor_func, environment: str, 
                        block_ms: int = 1000) -> None:
        """Consume messages from stream with acknowledgment."""
        try:
            logger.info(f"🎧 Consumer '{consumer_name}' in group '{group_name}' listening for environment '{environment}'")
            
            while True:
                # Read messages from stream (blocking)
                messages = self.redis_client.xreadgroup(
                    group_name,
                    consumer_name,
                    {self.stream_name: '>'},  # '>' means new messages only
                    block=block_ms,
                    count=1  # Process one at a time
                )
                
                if messages:
                    for stream, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            try:
                                logger.info(f"📨 Consumer '{consumer_name}' received message {message_id} for environment '{environment}'")
                                
                                # Process the message
                                processor_func(message_data, environment)
                                
                                # Acknowledge successful processing
                                self.redis_client.xack(self.stream_name, group_name, message_id)
                                logger.info(f"✅ Consumer '{consumer_name}' acknowledged message {message_id} for environment '{environment}'")
                                
                            except Exception as e:
                                logger.error(f"❌ Consumer '{consumer_name}' failed to process message {message_id} for environment '{environment}': {e}")
                                # Don't acknowledge - message will be redelivered
                                
                else:
                    # No messages, continue loop
                    pass
                    
        except Exception as e:
            logger.error(f"❌ Consumer '{consumer_name}' error for environment '{environment}': {e}")
            raise 