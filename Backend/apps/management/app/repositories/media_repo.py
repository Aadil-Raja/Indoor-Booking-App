from sqlalchemy.orm import Session
from shared.models import CourtMedia, MediaType
from typing import Optional, List


def create(
    db: Session,
    *,
    media_type: str,
    url: str,
    property_id: Optional[int] = None,
    court_id: Optional[int] = None,
    thumbnail_url: Optional[str] = None,
    caption: Optional[str] = None,
    display_order: int = 0
) -> CourtMedia:
    """Create a new media entry"""
    media = CourtMedia(
        property_id=property_id,
        court_id=court_id,
        media_type=MediaType[media_type],
        url=url,
        thumbnail_url=thumbnail_url,
        caption=caption,
        display_order=display_order
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def get_by_id(db: Session, media_id: int) -> Optional[CourtMedia]:
    """Get media by ID"""
    return db.query(CourtMedia).filter(CourtMedia.id == media_id).first()


def get_by_property(db: Session, property_id: int) -> List[CourtMedia]:
    """Get all media for a property"""
    return (
        db.query(CourtMedia)
        .filter(CourtMedia.property_id == property_id)
        .order_by(CourtMedia.display_order, CourtMedia.created_at)
        .all()
    )


def get_by_court(db: Session, court_id: int) -> List[CourtMedia]:
    """Get all media for a court"""
    return (
        db.query(CourtMedia)
        .filter(CourtMedia.court_id == court_id)
        .order_by(CourtMedia.display_order, CourtMedia.created_at)
        .all()
    )


def update(db: Session, media: CourtMedia, **kwargs) -> CourtMedia:
    """Update media fields"""
    for key, value in kwargs.items():
        if value is not None and hasattr(media, key):
            setattr(media, key, value)
    db.commit()
    db.refresh(media)
    return media


def delete(db: Session, media: CourtMedia) -> None:
    """Delete media entry"""
    db.delete(media)
    db.commit()
