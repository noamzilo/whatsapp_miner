# src/db/models/whatsapp_messages.py

from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface


class WhatsAppMessage(DbInterface):
	__tablename__ = "whatsapp_messages"

	id = Column(Integer, primary_key=True)
	message_id = Column(Text, unique=True, nullable=False)
	sender_id = Column(Integer, ForeignKey("whatsapp_users.id"))
	group_id = Column(Integer, ForeignKey("whatsapp_groups.id"))
	timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
	raw_text = Column(Text, nullable=False)
	message_type = Column(Text)
	is_forwarded = Column(Boolean)
	llm_processed = Column(Boolean, nullable=False, server_default="false")
	is_real = Column(Boolean, nullable=False, server_default="true")
