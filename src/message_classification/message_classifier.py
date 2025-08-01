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
from sqlalchemy.orm import Session
from sqlalchemy import and_, not_

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import time
import random

# Import environment variables with fallbacks for testing
try:
    from src.env_var_injection import message_classifier_run_every_seconds, groq_api_key
except RuntimeError:
    # Fallback for testing without environment variables
    message_classifier_run_every_seconds = 30
    groq_api_key = "test_key"
from src.db.db import get_db_session
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_classification_prompt import LeadClassificationPrompt
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        self.classification_prompt = self._get_classification_prompt()
        
    def _get_classification_prompt(self) -> str:
        """Get the classification prompt from the database."""
        with get_db_session() as session:
            prompt = session.query(LeadClassificationPrompt).filter(
                LeadClassificationPrompt.template_name == "lead_classification"
            ).first()
            
            if not prompt:
                # Create default prompt if it doesn't exist
                default_prompt = LeadClassificationPrompt(
                    template_name="lead_classification",
                    prompt_text="""You are a classifier for WhatsApp messages from local groups to identify potential business leads.

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

Analyze the message and respond with a JSON object containing:
- is_lead: boolean - Set to true if the person is actively seeking a specific local business or service, false otherwise
- lead_category: string or null - The specific type of business they're looking for (e.g., "dentist", "plumber", "restaurant"). Use null if not a lead
- lead_description: string or null - A brief description of what they're seeking (e.g., "Looking for a dentist", "Need urgent plumbing help"). Use null if not a lead
- confidence_score: float between 0 and 1 - Your confidence in this classification (0.0 = very uncertain, 1.0 = very certain)
- reasoning: string - Brief explanation of why you classified it this way

Message: {message_text}""",
                    version="1.1"
                )
                session.add(default_prompt)
                session.commit()
                return default_prompt.prompt_text
            
            return prompt.prompt_text
    
    def _get_unclassified_messages(self, session: Session) -> List[WhatsAppMessage]:
        """Get all messages that haven't been classified yet."""
        return session.query(WhatsAppMessage).filter(
            not_(WhatsAppMessage.llm_processed)
        ).all()
    
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
    
    def _match_with_existing_categories(self, message_text: str, session: Session) -> Optional[str]:
        """Try to match the message with existing categories using LLM."""
        # Get all existing categories
        existing_categories = session.query(LeadCategory).all()
        
        if not existing_categories:
            return None
        
        # Create a list of existing category names
        category_names = [cat.name for cat in existing_categories]
        category_list = ", ".join(category_names)
        
        try:
            # Create messages for category matching
            system_message = f"""You are a helpful assistant that matches WhatsApp messages to existing lead categories.

Available categories: {category_list}

Your task is to determine if the message matches any of the existing categories.
IMPORTANT: Consider the full context of the original message, not just the classification result.
The message may contain important details that help determine the best category match.

If it matches, return the exact category name from the list above.
If it doesn't match any existing category, return "no_match".

Respond with ONLY the category name or "no_match"."""
            
            human_message = f"""Original message: {message_text}

Which category does this message match? Consider the full context and meaning of the message.
Respond with only the category name or "no_match"."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=human_message)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse the response
            matched_category = response.content.strip().lower()
            
            # Check if the matched category exists in our list
            if matched_category in [cat.name.lower() for cat in existing_categories]:
                # Find the original case-sensitive category name
                for cat in existing_categories:
                    if cat.name.lower() == matched_category:
                        return cat.name
            
            return None
            
        except Exception as e:
            logger.warning(f"Error matching with existing categories: {e}")
            return None

    def _get_or_create_lead_category(self, session: Session, category_name: str) -> LeadCategory:
        """Get or create a lead category."""
        category = session.query(LeadCategory).filter(
            LeadCategory.name == category_name
        ).first()
        
        if not category:
            category = LeadCategory(
                name=category_name,
                description=f"Category for {category_name} leads",
                opening_message_template=f"Hi! I saw you're looking for {category_name} services. How can I help?"
            )
            session.add(category)
            session.commit()
        
        return category
    
    def _get_or_create_intent_type(self, session: Session, intent_name: str) -> MessageIntentType:
        """Get or create a message intent type."""
        intent_type = session.query(MessageIntentType).filter(
            MessageIntentType.name == intent_name
        ).first()
        
        if not intent_type:
            intent_type = MessageIntentType(
                name=intent_name,
                description=f"Intent type for {intent_name}"
            )
            session.add(intent_type)
            session.commit()
        
        return intent_type
    
    def _create_classification_record(self, session: Session, message: WhatsAppMessage, 
                                   classification_result: ClassificationResult) -> MessageIntentClassification:
        """Create a classification record for a message."""
        # For lead messages, try to match with existing categories first
        if classification_result.is_lead and classification_result.lead_category:
            # Try to match with existing categories using the original message text
            matched_category = self._match_with_existing_categories(message.raw_text, session)
            
            if matched_category:
                # Use the matched existing category
                lead_category = session.query(LeadCategory).filter(
                    LeadCategory.name == matched_category
                ).first()
                logger.info(f"✅ Matched message to existing category: {matched_category}")
            else:
                # Create new category as before
                lead_category = self._get_or_create_lead_category(
                    session, classification_result.lead_category
                )
                logger.info(f"✅ Created new category: {classification_result.lead_category}")
        else:
            # For non-lead messages, use a general category
            lead_category = self._get_or_create_lead_category(session, "general")
        
        # Get or create intent type
        intent_type = self._get_or_create_intent_type(
            session, 
            "lead_seeking" if classification_result.is_lead else "general_message"
        )
        
        # Get the classification prompt
        prompt = session.query(LeadClassificationPrompt).filter(
            LeadClassificationPrompt.template_name == "lead_classification"
        ).first()
        
        # Create classification record
        classification = MessageIntentClassification(
            message_id=message.id,
            prompt_template_id=prompt.id,
            parsed_type_id=intent_type.id,  # Use the correct column name
            lead_category_id=lead_category.id,
            confidence_score=classification_result.confidence_score,
            raw_llm_output=classification_result.model_dump()
        )
        
        session.add(classification)
        session.commit()
        
        return classification
    
    def _create_lead_record(self, session: Session, message: WhatsAppMessage, 
                           classification: MessageIntentClassification,
                           classification_result: ClassificationResult) -> DetectedLead:
        """Create a lead record if the message was classified as a lead."""
        lead = DetectedLead(
            classification_id=classification.id,
            user_id=message.sender_id,
            group_id=message.group_id,
            lead_for=classification_result.lead_description
        )
        
        session.add(lead)
        session.commit()
        
        return lead
    
    def _mark_message_as_processed(self, session: Session, message: WhatsAppMessage):
        """Mark a message as processed."""
        message.llm_processed = True
        session.commit()
    
    def classify_messages(self):
        """Main method to classify all unclassified messages."""
        logger.info("🔍 Starting message classification process")
        
        with get_db_session() as session:
            unclassified_messages = self._get_unclassified_messages(session)
            
            if not unclassified_messages:
                logger.info("✅ No unclassified messages found")
                return
            
            logger.info(f"📝 Found {len(unclassified_messages)} unclassified messages")
            
            for message in unclassified_messages:
                try:
                    logger.info(f"🔍 Classifying message ID: {message.id}")
                    
                    # Classify the message
                    classification_result = self._classify_message(message.raw_text)
                    
                    # Create classification record
                    classification = self._create_classification_record(
                        session, message, classification_result
                    )
                    
                    # If it's a lead, create lead record
                    if classification_result.is_lead:
                        lead = self._create_lead_record(
                            session, message, classification, classification_result
                        )
                        logger.info(f"✅ Created lead record for message {message.id}")
                    
                    # Mark message as processed
                    self._mark_message_as_processed(session, message)
                    
                    logger.info(f"✅ Successfully classified message {message.id}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing message {message.id}: {e}")
                    continue
    
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
                self.classify_messages()
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