from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OwnerProfileBase(BaseModel):
    business_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class OwnerProfileCreate(OwnerProfileBase):
    pass


class OwnerProfileUpdate(OwnerProfileBase):
    pass


class OwnerProfileResponse(OwnerProfileBase):
    id: int
    user_id: int
    verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_properties: int
    total_courts: int
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    completed_bookings: int
    cancelled_bookings: int
    total_revenue: float
    pending_revenue: float
    confirmed_revenue: float


class RevenueByProperty(BaseModel):
    property_id: int
    property_name: str
    total_bookings: int
    total_revenue: float


class RecentBooking(BaseModel):
    id: int
    booking_date: str
    start_time: str
    end_time: str
    total_price: float
    status: str
    payment_status: str
    court_name: str
    property_name: str
    customer_name: str
    customer_email: str
