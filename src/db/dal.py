"""
Data Access Layer - Centralized imports from repository modules.
This file maintains backward compatibility while using the new repository structure.
"""

# Import all functions from repositories
from src.db.repositories.users_repo import (
    create_or_get_user,
    get_user_by_id,
    get_user_by_whatsapp_id
)

from src.db.repositories.groups_repo import (
    create_or_get_group,
    get_group_by_id,
    get_group_by_whatsapp_id
)

from src.db.repositories.messages_repo import (
    create_message,
    create_message_with_dependencies,
    create_fake_message_with_dependencies,
    get_unclassified_messages,
    mark_message_as_processed,
    get_message_by_id,
    get_message_by_message_id,
    update_messages_to_unprocessed,
    get_processed_messages_count,
    get_unprocessed_messages_count,
    get_total_messages_count
)

from src.db.repositories.classifications_repo import (
    create_classification_record,
    get_all_classifications,
    get_all_classifications_count,
    delete_all_classifications,
    get_classifications_count
)

from src.db.repositories.leads_repo import (
    create_lead_record,
    get_lead_by_id,
    get_total_leads_count,
    get_leads_count,
    get_all_leads,
    delete_all_leads
)

from src.db.repositories.categories_repo import (
    get_or_create_lead_category,
    get_all_categories,
    get_category_by_name,
    get_category_names,
    delete_all_categories,
    get_all_categories_count,
    get_categories_count
)

from src.db.queries.stats_queries import (
    get_lead_statistics,
    get_processing_summary
)

from src.db.queries.summary_queries import (
    get_detailed_lead_summary
)

# Import additional functions that need to be added to repositories
from sqlalchemy import func, and_, not_
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from contextlib import contextmanager

# Import all models at the top level
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType
from src.db.models.lead_classification_prompt import LeadClassificationPrompt

# Import database interface functionality
from src.db.db_interface import get_db_session, get_session_local


def get_or_create_intent_type(session, intent_name: str) -> int:
    """Get or create a message intent type, returns intent type ID."""
    intent_type = session.query(MessageIntentType).filter_by(name=intent_name).first()
    if not intent_type:
        intent_type = MessageIntentType(
            name=intent_name,
            description=f"Intent type for {intent_name}"
        )
        session.add(intent_type)
        session.flush()
    
    return intent_type.id


def get_classification_prompt(session, template_name: str = "lead_classification") -> int:
    """Get or create the classification prompt, returns prompt ID."""
    prompt = session.query(LeadClassificationPrompt).filter_by(template_name=template_name).first()
    if not prompt:
        # Create default prompt if it doesn't exist
        default_prompt = LeadClassificationPrompt(
            template_name="lead_classification",
                prompt_text="""You are a classifier for WhatsApp messages from local groups to identify potential business leads.

Your task is to identify when someone is actively seeking a specific local business or service. Focus on actionable leads where a business owner could reach out to offer their services.

AVAILABLE BUSINESS TYPES: {existing_categories}

CRITICAL RULES FOR LEAD DETECTION:
1. The message MUST show CLEAR INTENT to find a specific service or business
2. The person must be ACTIVELY SEEKING or ASKING for a service
3. General statements about businesses are NOT leads (e.g., "Centro. Tons of women's clothes.")
4. Questions asking WHERE to find something ARE leads (e.g., "Where can I find really cute clothes?")
5. Requests for recommendations ARE leads (e.g., "Can anyone recommend a good dentist?")
6. General conversation, greetings, or statements are NOT leads
7. Use business TYPE names like 'tire_shop', 'hair_salon', 'math_tutor' - not business names like 'Joe's Tires'
8. If the message matches an existing category above, use that exact name
9. If not, create a new specific business type name (e.g., 'yoga_instructor', 'pet_sitter', 'car_mechanic')

EXAMPLES OF LEADS (CLEAR INTENT):
- "Where can I find really cute clothes other than the mall? Dresses or 2pc sets?" → is_lead: true, lead_category: "women_clothes"
- "Looking for a dentist" → is_lead: true, lead_category: "dentist"
- "Need a plumber urgently" → is_lead: true, lead_category: "plumber"
- "Can anyone recommend a good restaurant?" → is_lead: true, lead_category: "restaurant"

EXAMPLES OF NOT LEADS (NO CLEAR INTENT):
- "Centro. Tons of women's clothes." → is_lead: false, lead_category: null
- "Great weather today!" → is_lead: false, lead_category: null
- "How is everyone doing?" → is_lead: false, lead_category: null

Analyze the message and respond with a JSON object containing:
- is_lead: boolean - Set to true if the person is actively seeking a specific local business or service, false otherwise
- lead_category: string or null - The specific type of business they're looking for (e.g., "dentist", "plumber", "restaurant"). Use null if not a lead
- lead_description: string or null - A brief description of what they're seeking (e.g., "Looking for a dentist", "Need urgent plumbing help"). Use null if not a lead
- reasoning: string - Brief explanation of why you classified it this way

Message: {message_text}""",
                version="1.2"
            )
        session.add(default_prompt)
        session.flush()
        return default_prompt.id
    
    return prompt.id


def match_with_existing_categories(session, message_text: str) -> Optional[str]:
    """Try to match the message with existing categories using LLM."""
    # Get all existing categories
    existing_categories = session.query(LeadCategory).all()
    
    if not existing_categories:
        return None
    
    # Create a list of existing category names
    category_names = [cat.name for cat in existing_categories]
    category_list = ", ".join(category_names)
    
    try:
        # Initialize LLM
        from langchain_groq import ChatGroq
        from langchain.schema import HumanMessage, SystemMessage
        from src.env_var_injection import groq_api_key
        
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192"
        )
        
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
        response = llm.invoke(messages)
        
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
        from src.utils.log import get_logger
        logger = get_logger(__name__)
        logger.warning(f"Error matching with existing categories: {e}")
        return None
