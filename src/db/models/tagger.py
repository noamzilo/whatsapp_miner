from sqlalchemy import Column, Integer, Text, ForeignKey
from src.db.db_interface import DbInterface

class Tagger(DbInterface):
	__tablename__ = "taggers"

	id = Column(Integer, primary_key=True)
	tagger_type_id = Column(Integer, ForeignKey("tagger_types.id"), nullable=False)
	identifier = Column(Text, nullable=False)
