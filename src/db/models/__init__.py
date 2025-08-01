# src/db/models/__init__.py

from src.db.db_interface import DbInterface

# Import all model classes so they're registered with Base.metadata
from .whatsapp_user import WhatsAppUser
from .whatsapp_group import WhatsAppGroup
from .whatsapp_message import WhatsAppMessage
from .lead_category import LeadCategory
from .message_intent_type import MessageIntentType
from .lead_classification_prompt import LeadClassificationPrompt
from .message_intent_classification import MessageIntentClassification
from .detected_lead import DetectedLead
from .registered_business import RegisteredBusiness
from .forwarded_lead import ForwardedLead
