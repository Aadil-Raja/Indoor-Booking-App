from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.repositories import property_repo, court_repo, pricing_repo, availability_repo, media_repo
from app.utils.response_utils import make_response
from shared.models import Property, Court, CourtPricing, Booking, BookingStatus
from datetime import date, time, datetime, timedelta
from typing import Optional


def search_properties(
    db: Session,
    *,
    city: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 20
):
    """Search and filter properties"""
    # Base query - only active properties
    query = db.query(Property).filter(Property.is_active == True)
    
    # Apply filters
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    
    # If sport_type or price filters, need to join with courts and pricing
    if sport_type or min_price is not None or max_price is not None:
        query = query.join(Property.courts).filter(Court.is_active == True)
        
        if sport_type:
            query = query.filter(Court.sport_type.ilike(f"%{sport_type}%"))
        
        if min_price is not None or max_price is not None:
            query = query.join(Court.pricing)
            if min_price is not None:
                query = query.filter(CourtPricing.price_per_hour >= min_price)
            if max_price is not None:
                query = query.filter(CourtPricing.price_per_hour <= max_price)
        
        # Distinct to avoid duplicates
        query = query.distinct()
    
    # Count total
    total = query.count()
    
    # Pagination
    offset = (page - 1) * limit
    properties = query.offset(offset).limit(limit).all()
    
    # Format response
    data = {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "city": p.city,
                "state": p.state,
                "address": p.address,
                "amenities": p.amenities,
                "maps_link": p.maps_link
            }
            for p in properties
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }
    
    return make_response(True, "Properties retrieved successfully", data=data)


def get_property_details(db: Session, *, property_id: int):
    """Get property details with courts and media"""
    property = (
        db.query(Property)
        .options(
            joinedload(Property.courts).joinedload(Court.media),
            joinedload(Property.media)
        )
        .filter(Property.id == property_id, Property.is_active == True)
        .first()
    )
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    # Format response
    data = {
        "id": property.id,
        "name": property.name,
        "description": property.description,
        "address": property.address,
        "city": property.city,
        "state": property.state,
        "country": property.country,
        "maps_link": property.maps_link,
        "phone": property.phone,
        "email": property.email,
        "amenities": property.amenities,
        "media": [
            {
                "id": m.id,
                "media_type": m.media_type.value,
                "url": m.url,
                "thumbnail_url": m.thumbnail_url,
                "caption": m.caption
            }
            for m in property.media
        ],
        "courts": [
            {
                "id": c.id,
                "name": c.name,
                "sport_type": c.sport_type,
                "description": c.description,
                "specifications": c.specifications,
                "amenities": c.amenities,
                "media": [
                    {
                        "id": m.id,
                        "media_type": m.media_type.value,
                        "url": m.url,
                        "thumbnail_url": m.thumbnail_url,
                        "caption": m.caption
                    }
                    for m in c.media
                ]
            }
            for c in property.courts if c.is_active
        ]
    }
    
    return make_response(True, "Property details retrieved successfully", data=data)


def get_court_details(db: Session, *, court_id: int):
    """Get court details with pricing and media"""
    court = (
        db.query(Court)
        .options(
            joinedload(Court.property),
            joinedload(Court.pricing),
            joinedload(Court.media)
        )
        .filter(Court.id == court_id, Court.is_active == True)
        .first()
    )
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    # Format response
    data = {
        "id": court.id,
        "name": court.name,
        "sport_type": court.sport_type,
        "description": court.description,
        "specifications": court.specifications,
        "amenities": court.amenities,
        "property": {
            "id": court.property.id,
            "name": court.property.name,
            "address": court.property.address,
            "city": court.property.city,
            "maps_link": court.property.maps_link
        },
        "pricing_rules": [
            {
                "id": p.id,
                "days": p.days,
                "start_time": p.start_time.isoformat(),
                "end_time": p.end_time.isoformat(),
                "price_per_hour": p.price_per_hour,
                "label": p.label
            }
            for p in court.pricing
        ],
        "media": [
            {
                "id": m.id,
                "media_type": m.media_type.value,
                "url": m.url,
                "thumbnail_url": m.thumbnail_url,
                "caption": m.caption
            }
            for m in court.media
        ]
    }
    
    return make_response(True, "Court details retrieved successfully", data=data)


def get_court_pricing_for_date(db: Session, *, court_id: int, date_val: date):
    """Get pricing for a specific court and date"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court or not court.is_active:
        return make_response(False, "Court not found", status_code=404)
    
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = date_val.weekday()
    
    # Get pricing rules for this day
    pricing_rules = (
        db.query(CourtPricing)
        .filter(
            CourtPricing.court_id == court_id,
            CourtPricing.days.contains([day_of_week])
        )
        .order_by(CourtPricing.start_time)
        .all()
    )
    
    if not pricing_rules:
        return make_response(False, "No pricing available for this date", status_code=404)
    
    data = {
        "date": date_val.isoformat(),
        "day_of_week": day_of_week,
        "pricing": [
            {
                "start_time": p.start_time.isoformat(),
                "end_time": p.end_time.isoformat(),
                "price_per_hour": p.price_per_hour,
                "label": p.label
            }
            for p in pricing_rules
        ]
    }
    
    return make_response(True, "Pricing retrieved successfully", data=data)


def get_available_slots(db: Session, *, court_id: int, date_val: date):
    """Get available time slots for a court on a specific date"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court or not court.is_active:
        return make_response(False, "Court not found", status_code=404)
    
    # Get day of week
    day_of_week = date_val.weekday()
    
    # Get pricing rules for this day
    pricing_rules = (
        db.query(CourtPricing)
        .filter(
            CourtPricing.court_id == court_id,
            CourtPricing.days.contains([day_of_week])
        )
        .order_by(CourtPricing.start_time)
        .all()
    )
    
    if not pricing_rules:
        return make_response(False, "Court not available on this date", status_code=404)
    
    # Get blocked slots
    blocked_slots = availability_repo.get_by_date(db, court_id, date_val)
    
    # Get existing bookings
    bookings = (
        db.query(Booking)
        .filter(
            Booking.court_id == court_id,
            Booking.booking_date == date_val,
            Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed])
        )
        .all()
    )
    
    # Build available slots
    available_slots = []
    
    for pricing in pricing_rules:
        # Generate hourly slots within pricing time range
        current_time = datetime.combine(date_val, pricing.start_time)
        end_datetime = datetime.combine(date_val, pricing.end_time)
        
        while current_time < end_datetime:
            slot_start = current_time.time()
            slot_end = (current_time + timedelta(hours=1)).time()
            
            # Check if slot is blocked
            is_blocked = any(
                not (slot_end <= block.start_time or slot_start >= block.end_time)
                for block in blocked_slots
            )
            
            # Check if slot is booked
            is_booked = any(
                not (slot_end <= booking.start_time or slot_start >= booking.end_time)
                for booking in bookings
            )
            
            if not is_blocked and not is_booked:
                available_slots.append({
                    "start_time": slot_start.isoformat(),
                    "end_time": slot_end.isoformat(),
                    "price_per_hour": pricing.price_per_hour,
                    "label": pricing.label
                })
            
            current_time += timedelta(hours=1)
    
    data = {
        "date": date_val.isoformat(),
        "court_id": court_id,
        "court_name": court.name,
        "available_slots": available_slots
    }
    
    return make_response(True, "Available slots retrieved successfully", data=data)
