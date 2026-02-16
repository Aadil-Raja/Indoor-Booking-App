from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, CheckConstraint, func
from sqlalchemy.orm import relationship
import enum
from .base import Base


class MediaType(enum.Enum):
    image = "image"
    video = "video"


class CourtMedia(Base):
    __tablename__ = "court_media"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=True)
    court_id = Column(Integer, ForeignKey("courts.id", ondelete="CASCADE"), nullable=True)
    media_type = Column(
        Enum(MediaType, name="media_type", create_type=True),
        nullable=False
    )
    url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    caption = Column(String(200))
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    property = relationship("Property", foreign_keys=[property_id], back_populates="media")
    court = relationship("Court", foreign_keys=[court_id], back_populates="media")
    
    __table_args__ = (
        CheckConstraint(
            "(property_id IS NOT NULL) OR (court_id IS NOT NULL)",
            name="check_property_or_court"
        ),
    )
