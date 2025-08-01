#!/usr/bin/env python3
"""
Message Classifier Service
Handles classification of WhatsApp messages using Groq LLM API.
"""

import time
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import random

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Import environment variables with fallbacks for testing
try:
    from src.env_var_injection import message_classifier_run_every_seconds, groq_api_key
except RuntimeError:
    # Fallback for testing without environment variables
    message_classifier_run_every_seconds = 30
    groq_api_key = "test_key"

# Import logging utilities
from src.utils.log import get_logger, setup_logger
from src.paths import logs_root

# Setup logging
setup_logger(logs_root)
logger = get_logger(__name__)


class ClassificationResult(BaseModel):
    """Pydantic model for structured LLM classification output."""
    is_lead: bool = Field(description="Whether this message represents a lead")
    lead_category: Optional[str] = Field(
        description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant', 'plumber', 'electrician', 'tutor', 'restaurant')"
    )
    lead_description: Optional[str] = Field(description="Description of what the person is looking for")
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Reasoning for the classification")


class MessageClassifier:
    """Handles classification of WhatsApp messages using Groq LLM API."""
    
    def __init__(self):
        # Initialize LLM
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192"
        )
        
        # Initialize output parser for structured JSON responses
        self.output_parser = PydanticOutputParser(pydantic_object=ClassificationResult)
        
    def _classify_message(self, message_text: str) -> ClassificationResult:
        """Classify a single message using Groq LLM with retry logic and structured output."""
        # Messages under 8 characters are automatically not leads
        if len(message_text.strip()) < 8:
            return ClassificationResult(
                is_lead=False,
                lead_category=None,
                lead_description=None,
                confidence_score=1.0,
                reasoning="Message too short (under 8 characters) to be a lead"
            )
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Create messages for LangChain with structured output instructions
                system_message = f"""You are a helpful assistant that classifies WhatsApp messages from local groups to identify potential business leads.

Your task is to identify when someone is actively seeking a specific local business or service. Focus on actionable leads where a business owner could reach out to offer their services.

For lead categories, be specific and actionable. Use precise business types like:
- dentist
- spanish_classes  
- restaurant
- plumber
- electrician
- tutor
- hair_salon
- mechanic
- yoga_studio
- gym
- pet_groomer
- house_cleaner
- landscaper
- photographer
- lawyer
- accountant
- real_estate_agent

Avoid generic categories like "local_service" or "business". Instead, identify the specific type of business that would be interested in this lead.

IMPORTANT: You must respond with a valid JSON object that matches this exact structure:
{{
    "is_lead": boolean - Set to true if the person is actively seeking a specific local business or service, false otherwise
    "lead_category": string or null - The specific type of business they're looking for (e.g., "dentist", "plumber", "restaurant"). Use null if not a lead
    "lead_description": string or null - A brief description of what they're seeking (e.g., "Looking for a dentist", "Need urgent plumbing help"). Use null if not a lead
    "confidence_score": float between 0 and 1 - Your confidence in this classification (0.0 = very uncertain, 1.0 = very certain)
    "reasoning": string - Brief explanation of why you classified it this way
}}

The JSON must be properly formatted and all fields are required."""
                
                human_message = f"""Analyze this WhatsApp message and classify it:

Message: {message_text}

Identify if this person is seeking a specific kind of local business or service. If yes, determine the exact type of business that would be interested in this person as a potential customer (lead).

Respond with ONLY a valid JSON object matching the structure above."""
                
                messages = [
                    SystemMessage(content=system_message),
                    HumanMessage(content=human_message)
                ]
                
                # Get response from LLM
                response = self.llm.invoke(messages)
                
                # Parse the response using Pydantic with error handling
                try:
                    result = self.output_parser.parse(response.content)
                    
                    # Post-process the category name to standardize it
                    if result.lead_category:
                        result.lead_category = self._standardize_category_name(result.lead_category)
                    
                    return result
                except Exception as parse_error:
                    logger.warning(f"Failed to parse LLM response, attempting to fix JSON: {parse_error}")
                    
                    # Try to extract JSON from the response if it's not properly formatted
                    import re
                    import json
                    
                    # Look for JSON in the response
                    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                    if json_match:
                        try:
                            json_str = json_match.group(0)
                            data = json.loads(json_str)
                            
                            # Standardize category name if present
                            lead_category = data.get('lead_category')
                            if lead_category:
                                lead_category = self._standardize_category_name(lead_category)
                            
                            # Create ClassificationResult from parsed JSON
                            return ClassificationResult(
                                is_lead=data.get('is_lead', False),
                                lead_category=lead_category,
                                lead_description=data.get('lead_description'),
                                confidence_score=data.get('confidence_score', 0.0),
                                reasoning=data.get('reasoning', 'Parsed from malformed response')
                            )
                        except json.JSONDecodeError:
                            pass
                    
                    # If this is the last attempt, raise the error
                    if attempt == max_retries - 1:
                        raise parse_error
                    
                    # Otherwise, retry with exponential backoff
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying classification in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
            
            except Exception as e:
                logger.error(f"Error classifying message (attempt {attempt + 1}/{max_retries}): {e}")
                
                # If this is the last attempt, return default classification
                if attempt == max_retries - 1:
                    return ClassificationResult(
                        is_lead=False,
                        lead_category=None,
                        lead_description=None,
                        confidence_score=0.0,
                        reasoning=f"Error in classification after {max_retries} attempts: {str(e)}"
                    )
                
                # Otherwise, retry with exponential backoff
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying classification in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
        
        # This should never be reached, but just in case
        return ClassificationResult(
            is_lead=False,
            lead_category=None,
            lead_description=None,
            confidence_score=0.0,
            reasoning="Failed to classify message after all retries"
        )
    
    def _standardize_category_name(self, category_name: str) -> str:
        """Standardize category name: lowercase, replace spaces with underscores."""
        if not category_name:
            return category_name
        
        # Convert to lowercase and replace spaces with underscores
        standardized = category_name.lower().replace(' ', '_')
        
        # Remove any special characters except underscores
        import re
        standardized = re.sub(r'[^a-z0-9_]', '', standardized)
        
        # Remove multiple consecutive underscores
        standardized = re.sub(r'_+', '_', standardized)
        
        # Remove leading/trailing underscores
        standardized = standardized.strip('_')
        
        return standardized
    
    def classify_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify a list of messages and return results with database operations to be performed."""
        logger.info(f"🔍 Starting classification of {len(messages)} messages")
        
        results = []
        
        for i, message_data in enumerate(messages, 1):
            try:
                message_id = message_data['id']
                message_text = message_data['raw_text']
                
                logger.info(f"🔍 Classifying message {i}/{len(messages)}: '{message_text[:50]}...'")
                
                # Classify the message
                classification_result = self._classify_message(message_text)
                
                logger.info(f"   📊 Result: {'LEAD' if classification_result.is_lead else 'NOT LEAD'}")
                if classification_result.is_lead:
                    logger.info(f"   🎯 Category: {classification_result.lead_category}")
                    logger.info(f"   📝 Description: {classification_result.lead_description}")
                logger.info(f"   🎯 Confidence: {classification_result.confidence_score:.2f}")
                
                # Prepare result for database operations
                result = {
                    'message_id': message_id,
                    'classification_result': classification_result,
                    'success': True
                }
                
                results.append(result)
                
                logger.info(f"   ✅ Successfully classified message {message_id}")
                
            except Exception as e:
                logger.error(f"   ❌ Error processing message {message_data.get('id', 'unknown')}: {e}")
                results.append({
                    'message_id': message_data.get('id', 'unknown'),
                    'classification_result': None,
                    'success': False,
                    'error': str(e)
                })
                continue
        
        logger.info(f"✅ Completed classification of {len(messages)} messages")
        return results
    
    def run_continuous(self):
        """Run the classifier in a continuous loop."""
        logger.info("🚀 Starting Message Classifier Service")
        logger.info(f"⏰ Running every {message_classifier_run_every_seconds} seconds")
        
        iteration = 0
        while True:
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"🔄 Iteration {iteration} - {current_time}")
            
            try:
                # This would be implemented by the service layer that coordinates
                # between the classifier and database operations
                logger.info("Classification iteration completed")
            except Exception as e:
                logger.error(f"❌ Error in classification iteration: {e}")
            
            # Sleep for the configured interval
            time.sleep(message_classifier_run_every_seconds)


if __name__ == "__main__":
    import os
    
    classifier = MessageClassifier()
    
    try:
        classifier.run_continuous()
    except KeyboardInterrupt:
        logger.info("🛑 Message Classifier Service stopped by user")
    except Exception as e:
        logger.error(f"❌ Message Classifier Service error: {e}")
        raise 