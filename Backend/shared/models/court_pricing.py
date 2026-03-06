from sqlalchemy import Column, Integer, Float, Time, String, DateTime, ForeignKey, func, ARRAY
from sqlalchemy.orm import relationship
from .base import Base


class CourtPricing(Base):
    __tablename__ = "court_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    court_id = Column(Integer, ForeignKey("courts.id", ondelete="CASCADE"), nullable=False, index=True)
    days = Column(ARRAY(Integer), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    price_per_hour = Column(Float, nullable=False)
    label = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    court = relationship("Court", back_populates="pricing")
