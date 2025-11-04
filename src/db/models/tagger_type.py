from sqlalchemy import Column, Integer, Text
from src.db.db_interface import DbInterface

class TaggerType(DbInterface):
	__tablename__ = "tagger_types"

	id = Column(Integer, primary_key=True)
	name = Column(Text, nullable=False, unique=True)

