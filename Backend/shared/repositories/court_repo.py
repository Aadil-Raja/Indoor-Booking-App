"""
Court repository for database operations.
"""
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


def search_courts_with_filters(
    db: Session,
    *,
    search: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    date_val: Optional[str] = None,
    start_time: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """
    Search courts with multiple filters
    
    Args:
        search: Search in court name or property address
        sport_type: Filter by sport type
        min_price: Minimum price per hour
        max_price: Maximum price per hour
        date_val: Date for availability check (YYYY-MM-DD)
        start_time: Start time for availability check (HH:MM)
        page: Page number for pagination
        limit: Items per page
    
    Returns:
        Tuple of (courts list, total count)
    """
    from shared.models import Property, CourtPricing, CourtMedia, Booking, BookingStatus, CourtAvailability
    from sqlalchemy import func, or_, and_, distinct
    from sqlalchemy.orm import joinedload
    from datetime import datetime, time as dt_time
    
    # Base query - only active courts with active properties
    query = (
        db.query(Court)
        .join(Property, Court.property_id == Property.id)
        .filter(Court.is_active == True, Property.is_active == True)
    )
    
    # Search filter (court name OR property address OR property name)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Court.name.ilike(search_pattern),
                Property.address.ilike(search_pattern),
                Property.name.ilike(search_pattern),
                Property.city.ilike(search_pattern)
            )
        )
    
    # Sport type filter
    if sport_type:
        query = query.filter(Court.sport_type.ilike(f"%{sport_type}%"))
    
    # Price filter - join with pricing table
    if min_price is not None or max_price is not None:
        query = query.join(CourtPricing, Court.id == CourtPricing.court_id)
        
        if min_price is not None:
            query = query.filter(CourtPricing.price_per_hour >= min_price)
        
        if max_price is not None:
            query = query.filter(CourtPricing.price_per_hour <= max_price)
        
        # Use distinct to avoid duplicates from multiple pricing rules
        query = query.distinct(Court.id)
    
    # Count total before pagination
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    courts = (
        query
        .options(
            joinedload(Court.property),
            joinedload(Court.media),
            joinedload(Court.pricing)
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return courts, total


def get_base_price(db: Session, court_id: int) -> Optional[float]:
    """
    Get the base (minimum) price for a court
    
    Args:
        court_id: Court ID
    
    Returns:
        Minimum price per hour or None
    """
    from shared.models import CourtPricing
    from sqlalchemy import func
    
    result = (
        db.query(func.min(CourtPricing.price_per_hour))
        .filter(CourtPricing.court_id == court_id)
        .scalar()
    )
    
    return result


def check_court_availability(
    db: Session,
    court_id: int,
    date_val: str,
    start_time: str
) -> bool:
    """
    Check if a court is available at a specific date and time
    
    Args:
        court_id: Court ID
        date_val: Date string (YYYY-MM-DD)
        start_time: Time string (HH:MM)
    
    Returns:
        True if available, False otherwise
    """
    from shared.models import Booking, BookingStatus, CourtAvailability, CourtPricing
    from datetime import datetime, timedelta
    
    try:
        # Parse date and time
        booking_date = datetime.strptime(date_val, "%Y-%m-%d").date()
        booking_time = datetime.strptime(start_time, "%H:%M").time()
        
        # Get day of week (0=Monday, 6=Sunday)
        day_of_week = booking_date.weekday()
        
        # Check if court has pricing for this day and time
        pricing_exists = (
            db.query(CourtPricing)
            .filter(
                CourtPricing.court_id == court_id,
                CourtPricing.days.any(day_of_week),
                CourtPricing.start_time <= booking_time,
                CourtPricing.end_time > booking_time
            )
            .first()
        )
        
        if not pricing_exists:
            return False
        
        # Check if slot is blocked by owner
        blocked = (
            db.query(CourtAvailability)
            .filter(
                CourtAvailability.court_id == court_id,
                CourtAvailability.date == booking_date,
                CourtAvailability.start_time <= booking_time,
                CourtAvailability.end_time > booking_time
            )
            .first()
        )
        
        if blocked:
            return False
        
        # Check if slot is already booked
        end_time = (datetime.combine(booking_date, booking_time) + timedelta(hours=1)).time()
        
        booked = (
            db.query(Booking)
            .filter(
                Booking.court_id == court_id,
                Booking.booking_date == booking_date,
                Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
                Booking.start_time < end_time,
                Booking.end_time > booking_time
            )
            .first()
        )
        
        if booked:
            return False
        
        return True
        
    except (ValueError, AttributeError):
        return False
