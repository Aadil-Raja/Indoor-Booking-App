from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime


class PropertyBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    address: str = Field(min_length=1, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="Pakistan", max_length=100)
    maps_link: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    amenities: List[str] = Field(default_factory=list)


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    maps_link: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    amenities: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PropertyResponse(PropertyBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PropertyListItem(BaseModel):
    id: int
    name: str
    city: Optional[str]
    state: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True
