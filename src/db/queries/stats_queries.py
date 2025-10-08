"""Statistical queries for database analytics."""

from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.message_intent_classification import MessageIntentClassification
from src.db.models.detected_lead import DetectedLead
from src.db.models.lead_category import LeadCategory
from src.db.models.message_intent_type import MessageIntentType


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
