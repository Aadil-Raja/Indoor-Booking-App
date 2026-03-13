from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from shared.models.court import SportType


class CourtBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sport_types: List[SportType] = Field(min_items=1)
    description: Optional[str] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    amenities: List[str] = Field(default_factory=list)


class CourtCreate(CourtBase):
    pass


class CourtUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sport_types: Optional[List[SportType]] = Field(None, min_items=1)
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
    sport_types: List[str]
    is_active: bool
    
    class Config:
        from_attributes = True
