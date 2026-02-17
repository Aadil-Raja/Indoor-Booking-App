from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from enum import Enum


class MediaTypeEnum(str, Enum):
    image = "image"
    video = "video"


class CourtMediaBase(BaseModel):
    media_type: MediaTypeEnum
    caption: Optional[str] = Field(None, max_length=200)
    display_order: int = Field(default=0, ge=0)


class CourtMediaCreate(CourtMediaBase):
    pass


class CourtMediaUpdate(BaseModel):
    caption: Optional[str] = Field(None, max_length=200)
    display_order: Optional[int] = Field(None, ge=0)


class CourtMediaResponse(CourtMediaBase):
    id: int
    property_id: Optional[int] = None
    court_id: Optional[int] = None
    url: str
    thumbnail_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    url: str
    thumbnail_url: Optional[str] = None
    public_id: str
    format: str
    resource_type: str
