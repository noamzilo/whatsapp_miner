from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface


class WhatsAppMessage(DbInterface):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
