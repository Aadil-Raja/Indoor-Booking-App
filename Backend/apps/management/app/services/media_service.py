from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.repositories import media_repo, property_repo, court_repo
from app.services.storage.storage_cloudinary import upload_file, delete_file
from app.utils.response_utils import make_response
from shared.schemas.media import CourtMediaCreate, CourtMediaUpdate
from typing import Optional


async def upload_property_media(
    db: Session,
    *,
    property_id: int,
    owner_id: int,
    file: UploadFile,
    data: CourtMediaCreate
):
    """Upload media for property"""
    # Verify property exists and belongs to owner
    property = property_repo.get_by_id(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        # Upload to Cloudinary
        upload_result = await upload_file(
            file,
            folder=f"properties/{property_id}",
            resource_type="auto"
        )
        
        # Create media entry
        media = media_repo.create(
            db,
            property_id=property_id,
            media_type=data.media_type.value,
            url=upload_result["url"],
            thumbnail_url=upload_result.get("thumbnail_url"),
            caption=data.caption,
            display_order=data.display_order
        )
        
        return make_response(
            True,
            "Media uploaded successfully",
            data={
                "id": media.id,
                "url": media.url,
                "thumbnail_url": media.thumbnail_url,
                "media_type": media.media_type.value
            },
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to upload media", status_code=500, error=str(e))


async def upload_court_media(
    db: Session,
    *,
    court_id: int,
    owner_id: int,
    file: UploadFile,
    data: CourtMediaCreate
):
    """Upload media for court"""
    # Verify court exists and belongs to owner
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        # Upload to Cloudinary
        upload_result = await upload_file(
            file,
            folder=f"courts/{court_id}",
            resource_type="auto"
        )
        
        # Create media entry
        media = media_repo.create(
            db,
            court_id=court_id,
            media_type=data.media_type.value,
            url=upload_result["url"],
            thumbnail_url=upload_result.get("thumbnail_url"),
            caption=data.caption,
            display_order=data.display_order
        )
        
        return make_response(
            True,
            "Media uploaded successfully",
            data={
                "id": media.id,
                "url": media.url,
                "thumbnail_url": media.thumbnail_url,
                "media_type": media.media_type.value
            },
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to upload media", status_code=500, error=str(e))


def get_property_media(db: Session, *, property_id: int, owner_id: int):
    """Get all media for a property"""
    # Verify property exists and belongs to owner
    property = property_repo.get_by_id(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    media_list = media_repo.get_by_property(db, property_id)
    
    data = [
        {
            "id": m.id,
            "media_type": m.media_type.value,
            "url": m.url,
            "thumbnail_url": m.thumbnail_url,
            "caption": m.caption,
            "display_order": m.display_order
        }
        for m in media_list
    ]
    
    return make_response(True, "Media retrieved successfully", data=data)


def get_court_media(db: Session, *, court_id: int, owner_id: int):
    """Get all media for a court"""
    # Verify court exists and belongs to owner
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    media_list = media_repo.get_by_court(db, court_id)
    
    data = [
        {
            "id": m.id,
            "media_type": m.media_type.value,
            "url": m.url,
            "thumbnail_url": m.thumbnail_url,
            "caption": m.caption,
            "display_order": m.display_order
        }
        for m in media_list
    ]
    
    return make_response(True, "Media retrieved successfully", data=data)


def update_media(db: Session, *, media_id: int, owner_id: int, data: CourtMediaUpdate):
    """Update media metadata"""
    media = media_repo.get_by_id(db, media_id)
    
    if not media:
        return make_response(False, "Media not found", status_code=404)
    
    # Verify ownership
    if media.property_id:
        property = property_repo.get_by_id(db, media.property_id)
        if not property or property.owner_id != owner_id:
            return make_response(False, "Access denied", status_code=403)
    elif media.court_id:
        court = court_repo.get_by_id(db, media.court_id)
        property = property_repo.get_by_id(db, court.property_id)
        if not property or property.owner_id != owner_id:
            return make_response(False, "Access denied", status_code=403)
    
    try:
        updated = media_repo.update(db, media, **data.model_dump(exclude_unset=True))
        return make_response(
            True,
            "Media updated successfully",
            data={"id": updated.id}
        )
    except Exception as e:
        return make_response(False, "Failed to update media", status_code=500, error=str(e))


async def delete_media(db: Session, *, media_id: int, owner_id: int):
    """Delete media"""
    media = media_repo.get_by_id(db, media_id)
    
    if not media:
        return make_response(False, "Media not found", status_code=404)
    
    # Verify ownership
    if media.property_id:
        property = property_repo.get_by_id(db, media.property_id)
        if not property or property.owner_id != owner_id:
            return make_response(False, "Access denied", status_code=403)
    elif media.court_id:
        court = court_repo.get_by_id(db, media.court_id)
        property = property_repo.get_by_id(db, court.property_id)
        if not property or property.owner_id != owner_id:
            return make_response(False, "Access denied", status_code=403)
    
    try:
        # Extract public_id from Cloudinary URL and delete from Cloudinary
        # URL format: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/v{version}/{public_id}.{format}
        if "cloudinary.com" in media.url:
            try:
                await delete_file(media.url)
            except Exception as e:
                print(f"Warning: Failed to delete from Cloudinary: {e}")
        
        # Delete from database
        media_repo.delete(db, media)
        return make_response(True, "Media deleted successfully")
    except Exception as e:
        return make_response(False, "Failed to delete media", status_code=500, error=str(e))
