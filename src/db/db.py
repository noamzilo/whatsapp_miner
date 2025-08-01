from sqlalchemy import func, and_, not_
from contextlib import contextmanager
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

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


# Database Operations
def create_or_get_user(session, whatsapp_id: str, display_name: str = "") -> int:
    """Create or get a user, returns user ID."""
    user = session.query(WhatsAppUser).filter_by(whatsapp_id=whatsapp_id).first()
    if not user:
        user = WhatsAppUser(whatsapp_id=whatsapp_id, display_name=display_name)
        session.add(user)
        session.flush()
    
    return user.id


def create_or_get_group(session, whatsapp_group_id: str, group_name: str = "") -> int:
    """Create or get a group, returns group ID."""
    group = session.query(WhatsAppGroup).filter_by(whatsapp_group_id=whatsapp_group_id).first()
    if not group:
        group = WhatsAppGroup(
            whatsapp_group_id=whatsapp_group_id,
            group_name=group_name
        )
        session.add(group)
        session.flush()
    
    return group.id


def create_message(session, message_id: str, sender_id: int, group_id: int, 
                  raw_text: str, message_type: str = "text", 
                  is_forwarded: bool = False, timestamp: Optional[datetime] = None,
                  is_real: bool = True) -> int:
    """Create a message, returns message ID. Ensures user and group exist."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Check if message already exists
    existing = session.query(WhatsAppMessage).filter_by(message_id=message_id).first()
    if existing:
        return existing.id
    
    # Validate that user exists
    user = session.query(WhatsAppUser).filter_by(id=sender_id).first()
    if not user:
        raise ValueError(f"User with ID {sender_id} does not exist")
    
    # Validate that group exists
    group = session.query(WhatsAppGroup).filter_by(id=group_id).first()
    if not group:
        raise ValueError(f"Group with ID {group_id} does not exist")
    
    message = WhatsAppMessage(
        message_id=message_id,
        sender_id=sender_id,
        group_id=group_id,
        timestamp=timestamp,
        raw_text=raw_text,
        message_type=message_type,
        is_forwarded=is_forwarded,
        llm_processed=False,
        is_real=is_real
    )
    session.add(message)
    session.flush()
    
    return message.id


def create_message_with_dependencies(session, message_id: str, whatsapp_user_id: str, 
                                   whatsapp_group_id: str, raw_text: str, 
                                   user_display_name: str = "", group_name: str = "",
                                   message_type: str = "text", is_forwarded: bool = False, 
                                   timestamp: Optional[datetime] = None, is_real: bool = True) -> int:
    """Create a message with automatic user and group creation. Atomic operation."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    # Check if message already exists
    existing = session.query(WhatsAppMessage).filter_by(message_id=message_id).first()
    if existing:
        return existing.id
    
    # Create or get user
    user_id = create_or_get_user(session, whatsapp_user_id, user_display_name)
    
    # Create or get group
    group_id = create_or_get_group(session, whatsapp_group_id, group_name)
    
    # Create the message
    return create_message(session, message_id, user_id, group_id, raw_text, 
                        message_type, is_forwarded, timestamp, is_real)


def create_fake_message_with_dependencies(session, message_text: str, 
                                        user_id: int = 1, group_id: int = 1,
                                        message_id: Optional[str] = None) -> int:
    """Create a fake message with proper user and group dependencies."""
    import uuid
    
    # Generate unique message ID if not provided
    if message_id is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        message_id = f"fake_msg_{timestamp}_{unique_id}"
    
    # Create fake user if it doesn't exist
    user_whatsapp_id = f"user{user_id}@c.us"
    user_display_name = f"Test User {user_id}"
    
    # Create fake group if it doesn't exist
    group_whatsapp_id = f"group{group_id}@g.us"
    group_name = f"Test Group {group_id}"
    
    # Use the atomic operation with is_real=False for fake messages
    return create_message_with_dependencies(
        session=session,
        message_id=message_id,
        whatsapp_user_id=user_whatsapp_id,
        whatsapp_group_id=group_whatsapp_id,
        raw_text=message_text,
        user_display_name=user_display_name,
        group_name=group_name,
        is_real=False  # Fake messages are not real
    )


def get_unclassified_messages(session) -> List[Any]:
    """Get all messages that haven't been classified yet."""
    return session.query(WhatsAppMessage).filter(
        not_(WhatsAppMessage.llm_processed)
    ).all()


def mark_message_as_processed(session, message_id: int) -> None:
    """Mark a message as processed."""
    message = session.query(WhatsAppMessage).filter_by(id=message_id).first()
    if message:
        message.llm_processed = True
        session.commit()


def create_classification_record(session, message_id: int, prompt_template_id: int,
                               parsed_type_id: int, lead_category_id: int,
                               raw_llm_output: Dict[str, Any]) -> int:
    """Create a classification record."""
    classification = MessageIntentClassification(
        message_id=message_id,
        prompt_template_id=prompt_template_id,
        parsed_type_id=parsed_type_id,
        lead_category_id=lead_category_id,
        raw_llm_output=raw_llm_output
    )
    session.add(classification)
    session.flush()
    
    return classification.id


def create_lead_record(session, classification_id: int, user_id: int, 
                      group_id: int, lead_for: str) -> int:
    """Create a lead record."""
    lead = DetectedLead(
        classification_id=classification_id,
        user_id=user_id,
        group_id=group_id,
        lead_for=lead_for
    )
    session.add(lead)
    session.flush()
    
    return lead.id


def get_or_create_lead_category(session, category_name: str) -> int:
    """Get or create a lead category, returns category ID."""
    category = session.query(LeadCategory).filter_by(name=category_name).first()
    if not category:
        category = LeadCategory(
            name=category_name,
            description=f"Category for {category_name} leads",
            opening_message_template=f"Hi! I saw you're looking for {category_name} services. How can I help?"
        )
        session.add(category)
        session.flush()
    
    return category.id


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


# Query functions for lead statistics and summaries
def get_lead_statistics(session) -> Dict[str, Any]:
    """Get comprehensive lead statistics from the database."""
    # Total messages
    total_messages = session.query(WhatsAppMessage).count()
    
    # Processed messages
    processed_messages = session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == True
    ).count()
    
    # Unprocessed messages
    unprocessed_messages = session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == False
    ).count()
    
    # Total classifications
    total_classifications = session.query(MessageIntentClassification).count()
    
    # Total leads
    total_leads = session.query(DetectedLead).count()
    
    # Lead categories breakdown
    lead_categories = session.query(
        LeadCategory.name,
        func.count(DetectedLead.id).label('lead_count')
    ).join(MessageIntentClassification, LeadCategory.id == MessageIntentClassification.lead_category_id)\
     .join(DetectedLead, MessageIntentClassification.id == DetectedLead.classification_id)\
     .group_by(LeadCategory.name)\
     .order_by(func.count(DetectedLead.id).desc())\
     .all()
    
    # Intent types breakdown
    intent_types = session.query(
        MessageIntentType.name,
        func.count(MessageIntentClassification.id).label('classification_count')
    ).join(MessageIntentClassification, MessageIntentType.id == MessageIntentClassification.parsed_type_id)\
     .group_by(MessageIntentType.name)\
     .order_by(func.count(MessageIntentClassification.id).desc())\
     .all()
    
    # Recent leads (last 24 hours)
    from datetime import datetime, timedelta
    yesterday = datetime.now() - timedelta(days=1)
    recent_leads = session.query(DetectedLead).join(
        MessageIntentClassification, DetectedLead.classification_id == MessageIntentClassification.id
    ).join(
        WhatsAppMessage, MessageIntentClassification.message_id == WhatsAppMessage.id
    ).filter(
        WhatsAppMessage.timestamp >= yesterday
    ).count()
    
    return {
        'total_messages': total_messages,
        'processed_messages': processed_messages,
        'unprocessed_messages': unprocessed_messages,
        'total_classifications': total_classifications,
        'total_leads': total_leads,
        'lead_categories': lead_categories,
        'intent_types': intent_types,
        'recent_leads': recent_leads
    }


def get_detailed_lead_summary(session) -> List[Dict[str, Any]]:
    """Get detailed lead information with message details."""
    leads = session.query(
        DetectedLead.id.label('lead_id'),
        DetectedLead.lead_for,
        DetectedLead.created_at.label('lead_created_at'),
        WhatsAppMessage.id.label('message_id'),
        WhatsAppMessage.raw_text,
        WhatsAppMessage.timestamp.label('message_timestamp'),
        LeadCategory.name.label('category_name'),
        MessageIntentClassification.raw_llm_output,
        WhatsAppUser.display_name.label('sender_name'),
        WhatsAppGroup.group_name
    ).join(
        MessageIntentClassification, DetectedLead.classification_id == MessageIntentClassification.id
    ).join(
        WhatsAppMessage, MessageIntentClassification.message_id == WhatsAppMessage.id
    ).join(
        LeadCategory, MessageIntentClassification.lead_category_id == LeadCategory.id
    ).join(
        WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id
    ).join(
        WhatsAppGroup, WhatsAppMessage.group_id == WhatsAppGroup.id
    ).order_by(
        DetectedLead.created_at.desc()
    ).all()
    
    return [dict(lead._mapping) for lead in leads]


def get_processing_summary(session) -> Dict[str, Any]:
    """Get processing status summary."""
    # Processing status
    total_messages = session.query(WhatsAppMessage).count()
    processed_messages = session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == True
    ).count()
    unprocessed_messages = session.query(WhatsAppMessage).filter(
        WhatsAppMessage.llm_processed == False
    ).count()
    
    # Classification success rate
    total_classifications = session.query(MessageIntentClassification).count()
    successful_classifications = total_classifications  # All classifications are considered successful now
    
    processing_rate = (processed_messages / total_messages * 100) if total_messages > 0 else 0
    success_rate = (successful_classifications / total_classifications * 100) if total_classifications > 0 else 0
    
    return {
        'total_messages': total_messages,
        'processed_messages': processed_messages,
        'unprocessed_messages': unprocessed_messages,
        'processing_rate': processing_rate,
        'total_classifications': total_classifications,
        'successful_classifications': successful_classifications,
        'success_rate': success_rate
    }