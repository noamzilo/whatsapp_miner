# src/db/models/__init__.py

from src.db.db_interface import DbInterface

# Import all model classes so they're registered with Base.metadata
from .whatsapp_message import WhatsAppMessage
