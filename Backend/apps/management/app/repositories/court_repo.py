from sqlalchemy.orm import Session
from shared.models import Court
from typing import Optional, List


def create(db: Session, *, property_id: int, name: str, sport_type: str, **kwargs) -> Court:
    """Create a new court"""
    court = Court(property_id=property_id, name=name, sport_type=sport_type, **kwargs)
    db.add(court)
    db.commit()
    db.refresh(court)
    return court


def get_by_id(db: Session, court_id: int) -> Optional[Court]:
    """Get court by ID"""
    return db.query(Court).filter(Court.id == court_id).first()


def get_by_property(db: Session, property_id: int) -> List[Court]:
    """Get all courts for a property"""
    return db.query(Court).filter(Court.property_id == property_id).order_by(Court.created_at.desc()).all()


def update(db: Session, court: Court, **kwargs) -> Court:
    """Update court fields"""
    for key, value in kwargs.items():
        if value is not None and hasattr(court, key):
            setattr(court, key, value)
    db.commit()
    db.refresh(court)
    return court


def delete(db: Session, court: Court) -> None:
    """Delete court"""
    db.delete(court)
    db.commit()
