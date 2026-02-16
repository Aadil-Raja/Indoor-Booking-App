from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import relationship
from .base import Base


class CourtAvailability(Base):
    __tablename__ = "court_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    court_id = Column(Integer, ForeignKey("courts.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    reason = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    court = relationship("Court", back_populates="availability")
    
    __table_args__ = (
        Index('ix_court_availability_court_date', 'court_id', 'date'),
    )
