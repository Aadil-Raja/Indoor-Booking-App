from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import time, datetime


class CourtPricingBase(BaseModel):
    days: List[int] = Field(min_length=1, max_length=7)
    start_time: time
    end_time: time
    price_per_hour: float = Field(gt=0)
    label: Optional[str] = Field(None, max_length=100)
    
    @field_validator('days')
    @classmethod
    def validate_days(cls, v):
        """Validate days are between 0-6 (Monday-Sunday)"""
        if not all(0 <= day <= 6 for day in v):
            raise ValueError('Days must be between 0 (Monday) and 6 (Sunday)')
        if len(v) != len(set(v)):
            raise ValueError('Duplicate days not allowed')
        return sorted(v)
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Validate end_time is after start_time"""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class CourtPricingCreate(CourtPricingBase):
    pass


class CourtPricingUpdate(BaseModel):
    days: Optional[List[int]] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    price_per_hour: Optional[float] = Field(None, gt=0)
    label: Optional[str] = Field(None, max_length=100)


class CourtPricingResponse(CourtPricingBase):
    id: int
    court_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
