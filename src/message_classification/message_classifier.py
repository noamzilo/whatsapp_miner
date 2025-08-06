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
from src.db.db import get_category_names, get_message_by_id, get_lead_by_id, get_total_leads_count

# Get logger (setup_logger should only be called in main runner files)
logger = get_logger(__name__)


class ClassificationResult(BaseModel):
    """Pydantic model for structured LLM classification output."""
    is_lead: bool = Field(description="Whether this message represents a lead")
    lead_category: Optional[str] = Field(
        description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant', 'plumber', 'electrician', 'tutor', 'restaurant')"
    )
    lead_description: Optional[str] = Field(description="Description of what the person is looking for")
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
        
        # Store configuration
        self.run_every_seconds = message_classifier_run_every_seconds
        
    def _get_existing_categories(self, session) -> List[str]:
        """Get all existing category names from database."""
        return get_category_names(session)
    
    def _build_dynamic_prompt(self, existing_categories: List[str], is_retry: bool = False) -> str:
        """Build dynamic prompt with existing categories."""
        categories_text = ", ".join(existing_categories) if existing_categories else "none"
        
        retry_emphasis = ""
        if is_retry:
            retry_emphasis = """
IMPORTANT: This is a retry. The previous classification was too generic.
You MUST use a specific business type name, not a generic term."""
        
        return f"""Classify this WhatsApp message as either a business lead or not a lead.

EXISTING CATEGORIES: {categories_text}

CRITICAL RULES FOR LEAD DETECTION:
1. The message MUST show CLEAR INTENT to find a specific service or business
2. The person must be ACTIVELY SEEKING or ASKING for a service
3. General statements about businesses are NOT leads (e.g., "There are many smoke shops around here")
4. Questions asking WHERE to find something ARE leads (e.g., "Where are super cool glasses around here?")
5. Requests for recommendations ARE leads (e.g., "Can anyone recommend a good dentist?")
6. General conversation, greetings, or statements are NOT leads

EXAMPLES OF LEADS (CLEAR INTENT):
- "Where can I find really cute glasses other than jack's shop? not sunglasses!" → is_lead: true, lead_category: "women_clothes"
- "Looking for a dentist" → is_lead: true, lead_category: "dentist"
- "Need a plumber urgently" → is_lead: true, lead_category: "plumber"
- "Can anyone recommend a good restaurant?" → is_lead: true, lead_category: "restaurant"
- "Looking for a math tutor for my daughter" → is_lead: true, lead_category: "math_tutor"

EXAMPLES OF NOT LEADS (NO CLEAR INTENT):
- "Centro. Tons of women's clothes." → is_lead: false, lead_category: null
- "Great weather today!" → is_lead: false, lead_category: null
- "How is everyone doing?" → is_lead: false, lead_category: null
- "I love this group" → is_lead: false, lead_category: null
- "There's a new store opening" → is_lead: false, lead_category: null{retry_emphasis}

Respond with ONLY this JSON structure:
{{
    "is_lead": boolean,
    "lead_category": string or null,
    "lead_description": string or null,
    "reasoning": string
}}"""
    
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
1. The category should be a specific business type (e.g., 'hair_salon', 'math_tutor', 'car_mechanic', 'women_clothes', 'house_cleaner')
2. It should NOT be generic (e.g., 'general', 'business', 'service', 'store', 'shop')
3. If the category is too generic or wrong, suggest a better one
4. If the category is correct and specific, confirm it
5. For clothing requests, prefer 'women_clothes', 'clothing_store', 'fashion_boutique'
6. For cleaning requests, prefer 'house_cleaner', 'cleaning_service', 'maid_service'

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
                                    data['reasoning'] = f"Invalid category '{lead_category}' - not a valid business type"
                                else:
                                    lead_category = validated_category
                            
                            # Create ClassificationResult from parsed JSON
                            return ClassificationResult(
                                is_lead=data.get('is_lead', False),
                                lead_category=lead_category,
                                lead_description=data.get('lead_description'),
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
        
        # If it's a lead but no specific category, try again with retry emphasis
        if result.is_lead and not result.lead_category:
            logger.info(f"🔄 Lead detected but no category provided, retrying with emphasis...")
            result = self._attempt_classification(message_text, existing_categories, is_retry=True)
        
        # Skip LLM validation for now to avoid "general" bias
        # if result.is_lead and result.lead_category:
        #     result = self._validate_classification_with_llm(message_text, result, existing_categories)
        
        return result
    
    def _validate_category(self, category_name: str) -> Optional[str]:
        """Validate and standardize category name. Returns None if invalid."""
        if not category_name:
            return None
        
        # Standardize the category name
        standardized = self._standardize_category_name(category_name)
        
        # Only reject if it's clearly too short
        if len(standardized) < 3:
            logger.warning(f"Category too short '{category_name}' (standardized to '{standardized}')")
            return None
        
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
        logger.info("=" * 80)
        logger.info(f"🚀 STARTING BATCH CLASSIFICATION")
        logger.info(f"📊 Batch Size: {len(messages)} messages")
        logger.info("=" * 80)
        
        results = []
        
        for i, message_data in enumerate(messages, 1):
            message_start_time = datetime.now()
            try:
                message_id = message_data['id']
                message_text = message_data['raw_text']
                
                # Clear message separator
                logger.info("")
                logger.info("_" * 60)
                logger.info(f"📝 MESSAGE {i}/{len(messages)} (ID: {message_id})")
                logger.info(f"📄 Text: {message_text[:100]}{'...' if len(message_text) > 100 else ''}")
                
                # Classify the message with session for database-aware validation
                classification_result = self._classify_message(message_text, session)
                
                # Calculate processing time
                processing_time = (datetime.now() - message_start_time).total_seconds()
                
                # Clean, single-line logging for each data point
                logger.info(f"⏱️  Time: {processing_time:.2f}s")
                logger.info(f"🎯 Result: {'LEAD' if classification_result.is_lead else 'NOT LEAD'}")
                
                if classification_result.is_lead:
                    logger.info(f"📂 Category: {classification_result.lead_category}")
                    logger.info(f"📝 Description: {classification_result.lead_description or 'None'}")
                else:
                    logger.info(f"📝 Type: General conversation")
                
                logger.info(f"💭 Reasoning: {classification_result.reasoning[:150]}{'...' if len(classification_result.reasoning) > 150 else ''}")
                logger.info(f"📏 Length: {len(message_text)} chars")
                
                # Prepare result for database operations
                result = {
                    'message_id': message_id,
                    'classification_result': classification_result,
                    'success': True,
                    'processing_time_seconds': processing_time
                }
                
                results.append(result)
                
                logger.info(f"✅ Status: Success")
                
            except Exception as e:
                processing_time = (datetime.now() - message_start_time).total_seconds()
                logger.error(f"❌ Status: Error - {e}")
                results.append({
                    'message_id': message_data.get('id', 'unknown'),
                    'classification_result': None,
                    'success': False,
                    'error': str(e),
                    'processing_time_seconds': processing_time
                })
                continue
        
        # Batch completion summary
        total_processing_time = sum(r.get('processing_time_seconds', 0) for r in results)
        successful_classifications = sum(1 for r in results if r['success'])
        leads_detected = sum(1 for r in results if r['success'] and r['classification_result'].is_lead)
        
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🏁 BATCH COMPLETED")
        logger.info(f"📊 Processed: {successful_classifications}/{len(messages)} messages")
        logger.info(f"🎯 Leads: {leads_detected}")
        logger.info(f"⏱️  Total Time: {total_processing_time:.2f}s")
        logger.info(f"⚡ Avg Time: {total_processing_time/len(messages):.2f}s per message")
        logger.info("=" * 80)
        logger.info("")
        
        return results
    
    def process_classification_results(self, classification_results: List[Dict[str, Any]], session) -> int:
        """Process classification results and update database. Returns number of processed messages."""
        from src.db.db import (
            mark_message_as_processed, create_classification_record,
            create_lead_record, get_or_create_lead_category, get_or_create_intent_type,
            get_classification_prompt, match_with_existing_categories
        )
        
        logger.info("")
        logger.info("🗄️  DATABASE PROCESSING")
        logger.info(f"📊 Processing {len(classification_results)} results")
        
        processed_count = 0
        leads_created = 0
        categories_created = 0
        
        for result in classification_results:
            if not result['success']:
                logger.error(f"❌ Failed to classify message {result['message_id']}: {result.get('error', 'Unknown error')}")
                continue
                
            message_id = result['message_id']
            classification_result = result['classification_result']
            processing_time = result.get('processing_time_seconds', 0)
            
            logger.info(f"🗄️  Message {message_id}: Processing DB operations (LLM: {processing_time:.2f}s)")
            
            try:
                # Get or create intent type
                intent_name = "lead_seeking" if classification_result.is_lead else "general_message"
                intent_type_id = get_or_create_intent_type(session, intent_name)
                logger.debug(f"   📋 Intent type: {intent_name} (ID: {intent_type_id})")
                
                # Get classification prompt
                prompt_template_id = get_classification_prompt(session)
                logger.debug(f"   📝 Prompt template ID: {prompt_template_id}")
                
                # Handle lead category - ONLY for leads
                lead_category_id = None
                if classification_result.is_lead:
                    if classification_result.lead_category:
                        # Try to match with existing categories first
                        matched_category = match_with_existing_categories(session, classification_result.lead_category)
                        
                        if matched_category:
                            # Use the matched existing category
                            lead_category_id = get_or_create_lead_category(session, matched_category)
                            logger.info(f"   🎯 Matched to existing category: {matched_category} (ID: {lead_category_id})")
                        else:
                            # Create new category
                            lead_category_id = get_or_create_lead_category(session, classification_result.lead_category)
                            categories_created += 1
                            logger.info(f"   🆕 Created new category: {classification_result.lead_category} (ID: {lead_category_id})")
                    else:
                        # Lead but no category - skip this lead for now
                        logger.warning(f"   ⚠️  Lead detected but no category specified, skipping message {message_id}")
                        continue
                else:
                    # For non-leads, don't create any classification record
                    logger.debug(f"   📝 Non-lead message {message_id} - no classification record needed")
                
                # Create classification record ONLY for leads
                if classification_result.is_lead:
                    classification_id = create_classification_record(
                        session=session,
                        message_id=message_id,
                        prompt_template_id=prompt_template_id,
                        parsed_type_id=intent_type_id,
                        lead_category_id=lead_category_id,
                        raw_llm_output=classification_result.model_dump()
                    )
                    logger.info(f"   📊 Created classification record (ID: {classification_id})")
                    
                    # Create lead record ONLY for leads
                    message = get_message_by_id(session, message_id)
                    
                    if message:
                        logger.info(f"   🎯 Creating lead record for message {message_id} (sender: {message.sender_id}, group: {message.group_id})")
                        lead_id = create_lead_record(
                            session=session,
                            classification_id=classification_id,
                            user_id=message.sender_id,
                            group_id=message.group_id,
                            lead_for=classification_result.lead_description or "Lead detected",
                            message_id=message_id,
                            lead_category_id=lead_category_id
                        )
                        leads_created += 1
                        logger.info(f"   🎯 SUCCESS: Created lead record (ID: {lead_id}) for user {message.sender_id} in group {message.group_id}")
                        logger.info(f"   📝 Lead description: {classification_result.lead_description}")
                        
                        # Verify the lead was actually created
                        created_lead = get_lead_by_id(session, lead_id)
                        if created_lead:
                            logger.info(f"   ✅ VERIFIED: Lead record {lead_id} exists in database")
                        else:
                            logger.error(f"   ❌ ERROR: Lead record {lead_id} was not found in database after creation")
                    else:
                        logger.error(f"   ❌ Could not find message {message_id} for lead creation")
                        continue
                else:
                    logger.debug(f"   📝 Non-lead message {message_id} - no lead record created")
                
                # Mark message as processed (for both leads and non-leads)
                mark_message_as_processed(session, message_id)
                logger.debug(f"   ✅ Marked message {message_id} as processed")
                
                # Commit the transaction for this message
                session.commit()
                logger.debug(f"   💾 Committed database changes for message {message_id}")
                
                processed_count += 1
                logger.info(f"   ✅ Successfully processed message {message_id} in database")
                
            except Exception as e:
                logger.error(f"   ❌ Error processing message {message_id} in database: {e}")
                session.rollback()
                logger.debug(f"   🔄 Rolled back database changes for message {message_id}")
                continue
        
        logger.info("")
        logger.info("🗄️  DATABASE PROCESSING COMPLETED")
        logger.info(f"📊 Processed: {processed_count}/{len(classification_results)} messages")
        logger.info(f"🎯 Leads: {leads_created}")
        logger.info(f"🆕 Categories: {categories_created}")
        
        # Final verification - count actual leads in database
        try:
            total_leads_in_db = get_total_leads_count(session)
            logger.info(f"🗄️  Total leads in database: {total_leads_in_db}")
        except Exception as e:
            logger.warning(f"Could not verify total leads in database: {e}")
        
        logger.info("")
        
        return processed_count
    
    def run_continuous(self):
        """Run the classifier in a continuous loop."""
        logger.info("🚀 Starting Message Classifier Service")
        logger.info(f"⏰ Running every {self.run_every_seconds} seconds")
        
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
            time.sleep(self.run_every_seconds)


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