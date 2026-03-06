from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, time, datetime
from enum import Enum


class BookingStatusEnum(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class PaymentStatusEnum(str, Enum):
    pending = "pending"
    paid = "paid"
    refunded = "refunded"


class BookingBase(BaseModel):
    court_id: int
    booking_date: date
    start_time: time
    end_time: time
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('booking_date')
    @classmethod
    def validate_date(cls, v):
        """Validate booking date is not in the past"""
        if v < date.today():
            raise ValueError('Cannot book dates in the past')
        return v
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Validate end_time is after start_time (handles XX:59 format and midnight crossing)"""
        if 'start_time' in info.data:
            start_time = info.data['start_time']
            # Allow XX:59 format (same hour) - e.g., 23:00 to 23:59
            if v.hour == start_time.hour and v.minute == 59:
                return v
            # Allow midnight crossing (e.g., 23:00 to 00:00)
            # If end_time is earlier than start_time, assume it's next day
            if v <= start_time:
                # Check if it's a valid midnight crossing (start_time >= 22:00 and end_time <= 06:00)
                if start_time.hour >= 22 and v.hour <= 6:
                    # Valid midnight crossing, allow it
                    pass
                else:
                    raise ValueError('end_time must be after start_time')
        return v


class BookingCreate(BookingBase):
    pass


class BookingResponse(BookingBase):
    id: int
    customer_id: int
    total_hours: float
    price_per_hour: float
    total_price: float
    status: BookingStatusEnum
    payment_status: PaymentStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BookingWithDetails(BookingResponse):
    court_name: str
    sport_type: str
    property_name: str
    property_address: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None


class BookingListItem(BaseModel):
    id: int
    booking_date: date
    start_time: time
    end_time: time
    total_price: float
    status: BookingStatusEnum
    payment_status: PaymentStatusEnum
    court_name: str
    property_name: str
    
    class Config:
        from_attributes = True
