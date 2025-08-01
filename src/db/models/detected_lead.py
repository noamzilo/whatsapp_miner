# src/db/models/detected_lead.py

from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface


class DetectedLead(DbInterface):
	__tablename__ = "detected_leads"

	id = Column(Integer, primary_key=True)
	classification_id = Column(Integer, ForeignKey("message_intent_classifications.id"), nullable=False)
	user_id = Column(Integer, ForeignKey("whatsapp_users.id"), nullable=False)
	group_id = Column(Integer, ForeignKey("whatsapp_groups.id"), nullable=False)
	lead_for = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
