from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from .base import Base


class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    address = Column(String(500), nullable=False)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="Pakistan")
    maps_link = Column(String(500))
    phone = Column(String(20))
    email = Column(String(100))
    amenities = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="properties")
    courts = relationship("Court", back_populates="property", cascade="all, delete-orphan")
    media = relationship("CourtMedia", foreign_keys="[CourtMedia.property_id]", back_populates="property", cascade="all, delete-orphan")
