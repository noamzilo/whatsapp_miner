# src/db/models/message_intent_classification.py

from sqlalchemy import Column, Integer, ForeignKey, Float, JSON, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface


class MessageIntentClassification(DbInterface):
	__tablename__ = "message_intent_classifications"

	id = Column(Integer, primary_key=True)
	message_id = Column(Integer, ForeignKey("whatsapp_messages.id"), nullable=False)
	prompt_template_id = Column(Integer, ForeignKey("lead_classification_prompts.id"), nullable=False)
	parsed_type_id = Column(Integer, ForeignKey("message_intent_types.id"), nullable=False)  # This is the actual column name in DB
	lead_category_id = Column(Integer, ForeignKey("lead_categories.id"), nullable=False)
	confidence_score = Column(Float)
	raw_llm_output = Column(JSON)
	classified_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
