# src/db/models/whatsapp_groups.py

from sqlalchemy import Column, Integer, Text, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface


class WhatsAppGroup(DbInterface):
	__tablename__ = "whatsapp_groups"

	id = Column(Integer, primary_key=True)
	whatsapp_group_id = Column(Text, unique=True, nullable=False)
	group_name = Column(Text)
	location_city = Column(Text)
	location_neighbourhood = Column(Text)
	location = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
