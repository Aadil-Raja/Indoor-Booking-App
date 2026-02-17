from sqlalchemy.orm import Session
from shared.models import CourtPricing
from typing import Optional, List
from datetime import time


def create(db: Session, *, court_id: int, days: List[int], start_time: time, end_time: time, price_per_hour: float, label: Optional[str] = None) -> CourtPricing:
    """Create a new pricing rule"""
    pricing = CourtPricing(
        court_id=court_id,
        days=days,
        start_time=start_time,
        end_time=end_time,
        price_per_hour=price_per_hour,
        label=label
    )
    db.add(pricing)
    db.commit()
    db.refresh(pricing)
    return pricing


def get_by_id(db: Session, pricing_id: int) -> Optional[CourtPricing]:
    """Get pricing by ID"""
    return db.query(CourtPricing).filter(CourtPricing.id == pricing_id).first()


def get_by_court(db: Session, court_id: int) -> List[CourtPricing]:
    """Get all pricing rules for a court"""
    return db.query(CourtPricing).filter(CourtPricing.court_id == court_id).order_by(CourtPricing.created_at.desc()).all()


def update(db: Session, pricing: CourtPricing, **kwargs) -> CourtPricing:
    """Update pricing fields"""
    for key, value in kwargs.items():
        if value is not None and hasattr(pricing, key):
            setattr(pricing, key, value)
    db.commit()
    db.refresh(pricing)
    return pricing


def delete(db: Session, pricing: CourtPricing) -> None:
    """Delete pricing rule"""
    db.delete(pricing)
    db.commit()


def check_overlap(db: Session, court_id: int, days: List[int], start_time: time, end_time: time, exclude_id: Optional[int] = None) -> bool:
    """Check if pricing rule overlaps with existing rules"""
    query = db.query(CourtPricing).filter(CourtPricing.court_id == court_id)
    
    if exclude_id:
        query = query.filter(CourtPricing.id != exclude_id)
    
    existing = query.all()
    
    for pricing in existing:
        # Check if any day overlaps
        if any(day in pricing.days for day in days):
            # Check if time ranges overlap
            if not (end_time <= pricing.start_time or start_time >= pricing.end_time):
                return True
    
    return False
