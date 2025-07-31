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
    lead_category: Optional[str] = Field(description="Category of the lead (e.g., 'dentist', 'spanish_classes', 'restaurant')")
    lead_description: Optional[str] = Field(description="Description of what the person is looking for")
    confidence_score: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Reasoning for the classification")


class MessageClassifier:
    """Handles classification of WhatsApp messages using Groq LLM API."""
    
    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192"
        )
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
                    prompt_text="""You are a classifier for WhatsApp messages from local groups. Your task is to determine if a message represents someone looking for a local service.

Services can include: dentist, spanish classes, restaurants, tutors, plumbers, electricians, and any other local business or service.

Analyze the message and respond with a JSON object containing:
- is_lead: boolean indicating if this is a lead
- lead_category: string describing the category (if it's a lead)
- lead_description: string describing what they're looking for (if it's a lead)
- confidence_score: float between 0 and 1
- reasoning: string explaining your classification

Message: {message_text}""",
                    version="1.0"
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
        """Classify a single message using Groq LLM."""
        try:
            # Format the prompt with the message
            formatted_prompt = self.classification_prompt.format(message_text=message_text)
            
            # Create messages for LangChain
            messages = [
                SystemMessage(content="You are a helpful assistant that classifies WhatsApp messages."),
                HumanMessage(content=formatted_prompt)
            ]
            
            # Get response from LLM
            response = self.llm.invoke(messages)
            
            # Parse the response using Pydantic
            result = self.output_parser.parse(response.content)
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying message: {e}")
            # Return a default classification
            return ClassificationResult(
                is_lead=False,
                lead_category=None,
                lead_description=None,
                confidence_score=0.0,
                reasoning=f"Error in classification: {str(e)}"
            )
    
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
        """Create a classification record in the database."""
        # Get or create lead category if it's a lead
        lead_category = None
        if classification_result.is_lead and classification_result.lead_category:
            lead_category = self._get_or_create_lead_category(session, classification_result.lead_category)
        
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
            intent_type_id=intent_type.id,
            lead_category_id=lead_category.id if lead_category else None,
            confidence_score=classification_result.confidence_score,
            raw_llm_output=classification_result.dict()
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