# src/db/models/registered_businesses.py

from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from src.db.db import Base


class RegisteredBusiness(Base):
	__tablename__ = "registered_businesses"

	id = Column(Integer, primary_key=True)
	business_name = Column(Text, nullable=False)
	contact_name = Column(Text)
	contact_phone = Column(Text)
	contact_email = Column(Text)
	lead_category_id = Column(Integer, ForeignKey("lead_categories.id"))
	service_area_city = Column(Text)
	service_area_neighbourhood = Column(Text)
	notes = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
