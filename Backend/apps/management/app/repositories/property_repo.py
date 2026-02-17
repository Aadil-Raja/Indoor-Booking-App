from sqlalchemy.orm import Session, joinedload
from shared.models import Property
from typing import Optional, List


def create(db: Session, *, owner_id: int, name: str, address: str, **kwargs) -> Property:
    """Create a new property"""
    property = Property(owner_id=owner_id, name=name, address=address, **kwargs)
    db.add(property)
    db.commit()
    db.refresh(property)
    return property


def get_by_id(db: Session, property_id: int) -> Optional[Property]:
    """Get property by ID"""
    return db.query(Property).filter(Property.id == property_id).first()


def get_by_owner(db: Session, owner_id: int) -> List[Property]:
    """Get all properties owned by user"""
    return db.query(Property).filter(Property.owner_id == owner_id).order_by(Property.created_at.desc()).all()


def get_with_courts(db: Session, property_id: int) -> Optional[Property]:
    """Get property with courts eagerly loaded"""
    return (
        db.query(Property)
        .options(joinedload(Property.courts))
        .filter(Property.id == property_id)
        .first()
    )


def update(db: Session, property: Property, **kwargs) -> Property:
    """Update property fields"""
    for key, value in kwargs.items():
        if value is not None and hasattr(property, key):
            setattr(property, key, value)
    db.commit()
    db.refresh(property)
    return property


def delete(db: Session, property: Property) -> None:
    """Delete property"""
    db.delete(property)
    db.commit()
