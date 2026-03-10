from enum import Enum
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, JSON, ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import relationship
from .base import Base


class SportType(str, Enum):
    """Enum for sport types"""
    futsal = "futsal"
    football = "football"
    cricket = "cricket"
    hockey = "hockey"
    padel = "padel"
    badminton = "badminton"
    tennis = "tennis"


class Court(Base):
    __tablename__ = "courts"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    sport_types = Column(ARRAY(PG_ENUM(SportType, name='sporttype', create_type=False)), nullable=False)
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
