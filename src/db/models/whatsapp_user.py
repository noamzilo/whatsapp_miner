# src/db/models/whatsapp_users.py

from sqlalchemy import Column, Integer, Text, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db import Base


class WhatsAppUser(Base):
	__tablename__ = "whatsapp_users"

	id = Column(Integer, primary_key=True)
	whatsapp_id = Column(Text, unique=True, nullable=False)
	display_name = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
