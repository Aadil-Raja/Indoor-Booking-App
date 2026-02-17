from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CourtBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sport_type: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    amenities: List[str] = Field(default_factory=list)


class CourtCreate(CourtBase):
    pass


class CourtUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sport_type: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    amenities: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CourtResponse(CourtBase):
    id: int
    property_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CourtListItem(BaseModel):
    id: int
    name: str
    sport_type: str
    is_active: bool
    
    class Config:
        from_attributes = True
