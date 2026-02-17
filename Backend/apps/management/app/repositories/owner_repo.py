from sqlalchemy.orm import Session
from shared.models import OwnerProfile
from typing import Optional


def create(db: Session, *, user_id: int, business_name: Optional[str] = None, phone: Optional[str] = None, address: Optional[str] = None) -> OwnerProfile:
    """Create owner profile"""
    profile = OwnerProfile(
        user_id=user_id,
        business_name=business_name,
        phone=phone,
        address=address
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_by_user_id(db: Session, user_id: int) -> Optional[OwnerProfile]:
    """Get owner profile by user ID"""
    return db.query(OwnerProfile).filter(OwnerProfile.user_id == user_id).first()


def update(db: Session, profile: OwnerProfile, **kwargs) -> OwnerProfile:
    """Update owner profile"""
    for key, value in kwargs.items():
        if value is not None and hasattr(profile, key):
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


def delete(db: Session, profile: OwnerProfile) -> None:
    """Delete owner profile"""
    db.delete(profile)
    db.commit()
