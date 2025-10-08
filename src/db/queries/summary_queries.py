"""Summary queries for detailed database information."""

from typing import List, Dict, Any
from src.db.models.detected_lead import DetectedLead
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup


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
