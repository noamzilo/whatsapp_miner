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
        
    def _get_existing_categories(self, session) -> List[str]:
        """Get all existing category names from database."""
        from src.db.models.lead_category import LeadCategory
        categories = session.query(LeadCategory.name).all()
        return [cat[0] for cat in categories]
    
    def _build_dynamic_prompt(self, existing_categories: List[str], is_retry: bool = False) -> str:
        """Build dynamic prompt with existing categories."""
        categories_text = ", ".join(existing_categories) if existing_categories else "none"
        
        retry_emphasis = ""
        if is_retry:
            retry_emphasis = """
IMPORTANT: This is a retry. The previous classification was too generic.
You MUST use a specific business type name, not a generic term."""
        
        return f"""You are a helpful assistant that classifies WhatsApp messages from local groups to identify potential business leads.

Your task is to identify when someone is actively seeking a specific local business or service. Focus on actionable leads where a business owner could reach out to offer their services.

EXISTING BUSINESS TYPES: {categories_text}

CRITICAL RULES:
1. Use business TYPE names like 'tire_shop', 'hair_salon', 'math_tutor' - not business names like 'Joe's Tires'
2. If the message matches an existing category above, use that exact name
3. If not, create a new specific business type name (e.g., 'yoga_instructor', 'pet_sitter', 'car_mechanic')
4. If the message is NOT seeking any specific business, set is_lead=false and lead_category=null
5. Always use specific business types, never generic terms like 'general', 'business', 'service'{retry_emphasis}

IMPORTANT: You must respond with a valid JSON object that matches this exact structure:
{{
    "is_lead": boolean - Set to true if the person is actively seeking a specific local business or service, false otherwise
    "lead_category": string or null - The specific type of business they're looking for (e.g., "dentist", "plumber", "restaurant"). Use null if not a lead
    "lead_description": string or null - A brief description of what they're seeking (e.g., "Looking for a dentist", "Need urgent plumbing help"). Use null if not a lead
    "confidence_score": float between 0 and 1 - Your confidence in this classification (0.0 = very uncertain, 1.0 = very certain)
    "reasoning": string - Brief explanation of why you classified it this way
}}

The JSON must be properly formatted and all fields are required."""
    
    def _validate_classification_with_llm(self, original_message: str, classification_result: ClassificationResult, existing_categories: List[str]) -> ClassificationResult:
        """Use LLM to validate and potentially fix the classification result."""
        if not classification_result.is_lead or not classification_result.lead_category:
            return classification_result
        
        # Build validation prompt
        categories_text = ", ".join(existing_categories) if existing_categories else "none"
        
        validation_prompt = f"""You are validating a business lead classification. 

Original message: "{original_message}"

Current classification:
- Category: {classification_result.lead_category}
- Description: {classification_result.lead_description}
- Confidence: {classification_result.confidence_score}

Available business types: {categories_text}

TASK: Validate if this classification is correct and specific.

RULES:
1. The category should be a specific business type (e.g., 'hair_salon', 'math_tutor', 'car_mechanic')
2. It should NOT be generic (e.g., 'general', 'business', 'service')
3. If the category is too generic or wrong, suggest a better one
4. If the category is correct and specific, confirm it

Respond with ONLY a JSON object:
{{
    "is_valid": boolean - true if the classification is correct and specific
    "suggested_category": string or null - better category if current one is generic/wrong, null if current is good
    "reasoning": string - brief explanation of your validation
}}

If the current classification is valid, respond with:
{{
    "is_valid": true,
    "suggested_category": null,
    "reasoning": "Category is specific and appropriate"
}}"""
        
        try:
            # Get LLM validation
            messages = [
                SystemMessage(content=validation_prompt),
                HumanMessage(content="Validate this classification.")
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse validation result
            import json
            validation_data = json.loads(response.content)
            
            if validation_data.get('is_valid', False):
                # Classification is valid
                return classification_result
            else:
                # Classification needs fixing
                suggested_category = validation_data.get('suggested_category')
                if suggested_category:
                    logger.info(f"LLM validation: '{classification_result.lead_category}' -> '{suggested_category}'")
                    classification_result.lead_category = self._standardize_category_name(suggested_category)
                    classification_result.reasoning += f" (validated and corrected by LLM: {validation_data.get('reasoning', '')})"
                else:
                    # No suggestion, mark as not a lead
                    logger.warning(f"LLM validation: '{classification_result.lead_category}' is invalid but no suggestion provided")
                    classification_result.is_lead = False
                    classification_result.lead_category = None
                    classification_result.lead_description = None
                    classification_result.confidence_score = 0.0
                    classification_result.reasoning = f"Invalid classification: {validation_data.get('reasoning', '')}"
                
                return classification_result
                
        except Exception as e:
            logger.warning(f"LLM validation failed: {e}, keeping original classification")
            return classification_result
    
    def _attempt_classification(self, message_text: str, existing_categories: List[str], is_retry: bool = False) -> ClassificationResult:
        """Attempt classification with given parameters."""
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
                # Build dynamic prompt
                system_message = self._build_dynamic_prompt(existing_categories, is_retry)
                
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
                    
                    # Validate and standardize the category name
                    if result.lead_category:
                        validated_category = self._validate_category(result.lead_category)
                        if validated_category is None:
                            # Invalid category - treat as not a lead
                            logger.warning(f"Invalid category '{result.lead_category}' detected, treating as not a lead")
                            result.is_lead = False
                            result.lead_category = None
                            result.lead_description = None
                            result.confidence_score = 0.0
                            result.reasoning = f"Invalid category '{result.lead_category}' - not a valid business type"
                        else:
                            result.lead_category = validated_category
                    
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
                            
                            # Validate and standardize category name if present
                            lead_category = data.get('lead_category')
                            if lead_category:
                                validated_category = self._validate_category(lead_category)
                                if validated_category is None:
                                    # Invalid category - treat as not a lead
                                    lead_category = None
                                    data['is_lead'] = False
                                    data['lead_description'] = None
                                    data['confidence_score'] = 0.0
                                    data['reasoning'] = f"Invalid category '{lead_category}' - not a valid business type"
                                else:
                                    lead_category = validated_category
                            
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
    
    def _classify_message(self, message_text: str, session=None) -> ClassificationResult:
        """Classify a single message using Groq LLM with database-aware validation."""
        # Get existing categories from database if session provided
        existing_categories = []
        if session:
            existing_categories = self._get_existing_categories(session)
        
        # First classification attempt
        result = self._attempt_classification(message_text, existing_categories, is_retry=False)
        
        # Validate classification with LLM
        if result.is_lead and result.lead_category:
            result = self._validate_classification_with_llm(message_text, result, existing_categories)
        
        return result
    
    def _validate_category(self, category_name: str) -> Optional[str]:
        """Validate and standardize category name. Returns None if invalid."""
        if not category_name:
            return None
        
        # Standardize the category name
        standardized = self._standardize_category_name(category_name)
        
        # Basic validation - reject obviously generic terms
        generic_terms = {'general', 'business', 'service', 'local', 'any', 'other'}
        if standardized.lower() in generic_terms:
            logger.warning(f"Generic category '{category_name}' (standardized to '{standardized}') - not a valid business type")
            return None
        
        # All other categories are valid (allow new business types)
        return standardized
    
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
    
    def classify_messages(self, messages: List[Dict[str, Any]], session=None) -> List[Dict[str, Any]]:
        """Classify a list of messages and return results with database operations to be performed."""
        logger.info(f"🔍 Starting classification of {len(messages)} messages")
        
        results = []
        
        for i, message_data in enumerate(messages, 1):
            try:
                message_id = message_data['id']
                message_text = message_data['raw_text']
                
                logger.info(f"🔍 Classifying message {i}/{len(messages)}: '{message_text[:50]}...'")
                
                # Classify the message with session for database-aware validation
                classification_result = self._classify_message(message_text, session)
                
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