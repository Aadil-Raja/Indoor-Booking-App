from sqlalchemy import Column, Integer, String, Date, Time, DateTime, ForeignKey, Float, Enum, func
from sqlalchemy.orm import relationship
import enum
from .base import Base


class BookingStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class PaymentStatus(enum.Enum):
    pending = "pending"
    paid = "paid"
    refunded = "refunded"


class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    court_id = Column(Integer, ForeignKey("courts.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    total_hours = Column(Float, nullable=False)
    price_per_hour = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(
        Enum(BookingStatus, name="booking_status", create_type=True),
        nullable=False,
        server_default=BookingStatus.pending.value,
        index=True
    )
    payment_status = Column(
        Enum(PaymentStatus, name="payment_status", create_type=True),
        nullable=False,
        server_default=PaymentStatus.pending.value,
    )
    notes = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="bookings")
    court = relationship("Court", back_populates="bookings")
