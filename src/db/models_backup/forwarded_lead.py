# src/db/models/forwarded_lead.py

from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, Index
from sqlalchemy.sql import func
from src.db.db_interface import DbInterface


class ForwardedLead(DbInterface):
	__tablename__ = "forwarded_leads"

	id = Column(Integer, primary_key=True)
	business_id = Column(Integer, ForeignKey("registered_businesses.id"), nullable=False)
	lead_id = Column(Integer, ForeignKey("detected_leads.id"), nullable=False)
	status = Column(Text, nullable=False, server_default="new")
	forwarded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
	notes = Column(Text)

	__table_args__ = (
		Index("ix_forwarded_leads_business_id_forwarded_at", "business_id", "forwarded_at"),
	)
