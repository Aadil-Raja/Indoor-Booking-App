from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from app.services import media_service
from shared.schemas.media import CourtMediaCreate, CourtMediaUpdate, MediaTypeEnum
from shared.models import User
from typing import Optional

router = APIRouter(tags=["Media"])


@router.post("/properties/{property_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_property_media(
    property_id: int,
    file: UploadFile = File(...),
    media_type: MediaTypeEnum = Form(...),
    caption: Optional[str] = Form(None),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Upload media for property (Owner only)"""
    data = CourtMediaCreate(
        media_type=media_type,
        caption=caption,
        display_order=display_order
    )
    return await media_service.upload_property_media(
        db,
        property_id=property_id,
        owner_id=current_user.id,
        file=file,
        data=data
    )


@router.post("/courts/{court_id}/media", status_code=status.HTTP_201_CREATED)
async def upload_court_media(
    court_id: int,
    file: UploadFile = File(...),
    media_type: MediaTypeEnum = Form(...),
    caption: Optional[str] = Form(None),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Upload media for court (Owner only)"""
    data = CourtMediaCreate(
        media_type=media_type,
        caption=caption,
        display_order=display_order
    )
    return await media_service.upload_court_media(
        db,
        court_id=court_id,
        owner_id=current_user.id,
        file=file,
        data=data
    )


@router.get("/properties/{property_id}/media")
def list_property_media(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """List all media for a property"""
    return media_service.get_property_media(db, property_id=property_id, owner_id=current_user.id)


@router.get("/courts/{court_id}/media")
def list_court_media(
    court_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """List all media for a court"""
    return media_service.get_court_media(db, court_id=court_id, owner_id=current_user.id)


@router.patch("/media/{media_id}")
def update_media(
    media_id: int,
    payload: CourtMediaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Update media metadata (caption, display_order)"""
    return media_service.update_media(db, media_id=media_id, owner_id=current_user.id, data=payload)


@router.delete("/media/{media_id}")
async def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Delete media"""
    return await media_service.delete_media(db, media_id=media_id, owner_id=current_user.id)
