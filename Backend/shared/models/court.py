from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from .base import Base


class Court(Base):
    __tablename__ = "courts"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sport_type = Column(String(50), nullable=False)
    description = Column(Text)
    specifications = Column(JSON, default=dict)
    amenities = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    property = relationship("Property", back_populates="courts")
    pricing = relationship("CourtPricing", back_populates="court", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="court", cascade="all, delete-orphan")
    media = relationship("CourtMedia", foreign_keys="[CourtMedia.court_id]", back_populates="court", cascade="all, delete-orphan")
    availability = relationship("CourtAvailability", back_populates="court", cascade="all, delete-orphan")
