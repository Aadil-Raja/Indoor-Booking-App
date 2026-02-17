from sqlalchemy.orm import Session
from shared.models import CourtAvailability
from typing import Optional, List
from datetime import date, time


def create(db: Session, *, court_id: int, date_val: date, start_time: time, end_time: time, reason: Optional[str] = None) -> CourtAvailability:
    """Create a new availability block"""
    availability = CourtAvailability(
        court_id=court_id,
        date=date_val,
        start_time=start_time,
        end_time=end_time,
        reason=reason
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability


def get_by_id(db: Session, availability_id: int) -> Optional[CourtAvailability]:
    """Get availability by ID"""
    return db.query(CourtAvailability).filter(CourtAvailability.id == availability_id).first()


def get_by_court(db: Session, court_id: int, from_date: Optional[date] = None) -> List[CourtAvailability]:
    """Get all blocked slots for a court"""
    query = db.query(CourtAvailability).filter(CourtAvailability.court_id == court_id)
    
    if from_date:
        query = query.filter(CourtAvailability.date >= from_date)
    
    return query.order_by(CourtAvailability.date, CourtAvailability.start_time).all()


def get_by_date(db: Session, court_id: int, date_val: date) -> List[CourtAvailability]:
    """Get blocked slots for a specific date"""
    return db.query(CourtAvailability).filter(
        CourtAvailability.court_id == court_id,
        CourtAvailability.date == date_val
    ).order_by(CourtAvailability.start_time).all()


def delete(db: Session, availability: CourtAvailability) -> None:
    """Delete availability block"""
    db.delete(availability)
    db.commit()


def check_overlap(db: Session, court_id: int, date_val: date, start_time: time, end_time: time) -> bool:
    """Check if time slot overlaps with existing blocks"""
    existing = get_by_date(db, court_id, date_val)
    
    for block in existing:
        if not (end_time <= block.start_time or start_time >= block.end_time):
            return True
    
    return False
