# src/db/models/message_intent_type.py

from sqlalchemy import Column, Integer, Text
from src.db.db_interface import DbInterface


class MessageIntentType(DbInterface):
	__tablename__ = "message_intent_types"

	id = Column(Integer, primary_key=True)
	name = Column(Text, unique=True, nullable=False)
	description = Column(Text)
