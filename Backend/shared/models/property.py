from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    address = Column(String(500))
    price_per_hour = Column(Float, nullable=False)
    capacity = Column(Integer)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
