from sqlalchemy import Column, Integer, String, DateTime, Enum, func
from sqlalchemy.orm import relationship
import enum
from .base import Base


class UserRole(enum.Enum):
    customer = "customer"
    owner = "owner"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    Name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(
        Enum(UserRole, name="user_role", create_type=True),
        nullable=False,
        server_default=UserRole.customer.value,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner_profile = relationship("OwnerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="owner", cascade="all, delete-orphan")
    bookings = relationship("Booking", foreign_keys="[Booking.customer_id]", back_populates="customer", cascade="all, delete-orphan")