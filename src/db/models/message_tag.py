from sqlalchemy import Column, Integer, Boolean, ForeignKey, TIMESTAMP, Float, Text
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface

class MessageTag(DbInterface):
	__tablename__ = "message_tags"

	id = Column(Integer, primary_key=True)
	message_id = Column(Integer, ForeignKey("whatsapp_messages.id"), nullable=False)
	is_lead = Column(Boolean, nullable=False)
	lead_category_id = Column(Integer, ForeignKey("lead_categories.id"), nullable=True)
	tagger_id = Column(Integer, ForeignKey("taggers.id"), nullable=False)
	tagged_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
	confidence_score = Column(Float, nullable=False, server_default="1.0")
	notes = Column(Text, nullable=True)

