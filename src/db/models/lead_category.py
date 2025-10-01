# src/db/models/lead_category.py

from sqlalchemy import Column, Integer, Text
from src.db.db_interface import DbInterface


class LeadCategory(DbInterface):
	__tablename__ = "lead_categories"

	id = Column(Integer, primary_key=True)
	name = Column(Text, unique=True, nullable=False)
	description = Column(Text)
	opening_message_template = Column(Text)
