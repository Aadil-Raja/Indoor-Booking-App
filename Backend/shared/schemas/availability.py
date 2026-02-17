from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, time, datetime


class CourtAvailabilityBase(BaseModel):
    date: date
    start_time: time
    end_time: time
    reason: Optional[str] = Field(None, max_length=200)
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        """Validate date is not in the past"""
        if v < date.today():
            raise ValueError('Cannot block dates in the past')
        return v
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Validate end_time is after start_time"""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class CourtAvailabilityCreate(CourtAvailabilityBase):
    pass


class CourtAvailabilityResponse(CourtAvailabilityBase):
    id: int
    court_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
