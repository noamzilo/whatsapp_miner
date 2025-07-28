# src/db/models/lead_classification_prompt.py

from sqlalchemy import Column, Integer, Text, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db import Base


class LeadClassificationPrompt(Base):
	__tablename__ = "lead_classification_prompts"

	id = Column(Integer, primary_key=True)
	template_name = Column(Text, unique=True, nullable=False)
	prompt_text = Column(Text, nullable=False)
	version = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
