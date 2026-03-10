"""
Public service for business logic operations accessible to all users.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, any_
from shared.repositories import property_repo, court_repo, pricing_repo, availability_repo
from shared.utils.response_utils import make_response
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
    """Search and filter properties with their courts"""
    # Base query - get courts with their properties and pricing
    query = (
        db.query(Court)
        .join(Court.property)
        .outerjoin(Court.pricing)
        .filter(Court.is_active == True, Property.is_active == True)
    )

    # Apply filters
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))

    if sport_type:
        query = query.filter(sport_type.lower() == any_(Court.sport_types))

    if min_price is not None:
        query = query.filter(CourtPricing.price_per_hour >= min_price)
    
    if max_price is not None:
        query = query.filter(CourtPricing.price_per_hour <= max_price)

        
    # Count total
    total = query.count()

    # Pagination
    offset = (page - 1) * limit
    courts = query.offset(offset).limit(limit).all()

    # Format response - return courts with property and pricing info
    items = []
    for court in courts:
        # Get minimum price for this court
        min_court_price = 0
        if court.pricing:
            min_court_price = min(p.price_per_hour for p in court.pricing)

        items.append({
            "id": court.id,
            "name": court.name,
            "sport_types": court.sport_types,
            "description": court.description,
            "min_price": min_court_price,
            "property": {
                "id": court.property.id,
                "name": court.property.name,
                "address": court.property.address,
                "city": court.property.city,
                "state": court.property.state,
                "maps_link": court.property.maps_link
            },
            "pricing_available": len(court.pricing) > 0
        })

    data = {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

    return make_response(True, "Courts retrieved successfully", data=data)


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
                "sport_types": c.sport_types,
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
    print(f"DEBUG: Getting court details for court_id: {court_id}")
    
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
    print(f"DEBUG: Court found: {court.name}")
    print(f"DEBUG: Pricing rules count: {len(court.pricing)}")
    for p in court.pricing:
        print(f"DEBUG: Pricing - ID: {p.id}, Time: {p.start_time}-{p.end_time}, Price: {p.price_per_hour}")


    # Format response
    # Calculate minimum price from pricing rules
    min_price = 0
    if court.pricing:
        min_price = min(p.price_per_hour for p in court.pricing)
        print(f"DEBUG: Calculated min_price: {min_price}")
    data = {
        "id": court.id,
        "name": court.name,
        "sport_types": court.sport_types,
        "description": court.description,
        "specifications": court.specifications,
        "amenities": court.amenities,
        "base_price": min_price,  # Add minimum price for frontend display
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

    print(f"DEBUG: Returning data with base_price: {data['base_price']}")
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
            CourtPricing.days.any(day_of_week)
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
            CourtPricing.days.any(day_of_week)
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

    # Get current time for filtering past slots (only for today)
    from datetime import datetime as dt
    now = dt.now()
    is_today = date_val == now.date()
    current_hour = now.hour if is_today else -1  # -1 means no filtering needed
    
    print(f"DEBUG: Is today: {is_today}, Current hour: {current_hour}")

    for pricing in pricing_rules:
        # Generate hourly slots within pricing time range
        current_time = datetime.combine(date_val, pricing.start_time)
        end_time_dt = datetime.combine(date_val, pricing.end_time)
        
        # If end time is earlier than start time (e.g., 23:59 on same day), it's still valid
        # If end time is much earlier (e.g., 00:00 vs 23:00), it means next day
        if pricing.end_time < pricing.start_time:
            # Midnight crossing - add one day to end time
            end_time_dt = datetime.combine(date_val + timedelta(days=1), pricing.end_time)
        
        print(f"DEBUG: Start: {current_time}, End: {end_time_dt}")

        # Generate hourly slots
        slot_count = 0
        max_slots = 24  # Safety limit to prevent infinite loops
        
        while current_time < end_time_dt and slot_count < max_slots:
            slot_start = current_time.time()
            print(f"DEBUG: Checking slot at {slot_start}")
            
            # Skip past time slots for today
            if is_today and current_time.hour <= current_hour:
                print(f"DEBUG: Skipping past slot {slot_start}")
                current_time += timedelta(hours=1)
                slot_count += 1
                continue
            
            # Calculate slot end - use XX:59 format to match pricing rules
            # This ensures booking end times match pricing rule end times
            slot_end = time(current_time.hour, 59)

            # Check if slot is blocked
            is_blocked = any(
                not (slot_end <= block.start_time or slot_start >= block.end_time)
                for block in blocked_slots
            )
            print(f"DEBUG: Slot {slot_start}-{slot_end} blocked: {is_blocked}")

            # Check if slot is booked
            is_booked = any(
                not (slot_end <= booking.start_time or slot_start >= booking.end_time)
                for booking in bookings
            )
            print(f"DEBUG: Slot {slot_start}-{slot_end} booked: {is_booked}")

            if not is_blocked and not is_booked:
                available_slots.append({
                    "start_time": slot_start.isoformat(),
                    "end_time": slot_end.isoformat(),
                    "price_per_hour": pricing.price_per_hour,
                    "label": pricing.label
                })
                

            current_time += timedelta(hours=1)
        slot_count += 1
        
        if slot_count >= max_slots:
            print(f"DEBUG: WARNING - Hit max slots limit for pricing rule {pricing.id}")

    print(f"DEBUG: Total available slots: {len(available_slots)}")
    

    data = {
        "date": date_val.isoformat(),
        "court_id": court_id,
        "court_name": court.name,
        "available_slots": available_slots
    }

    return make_response(True, "Available slots retrieved successfully", data=data)



def search_courts(
    db: Session,
    *,
    search: Optional[str] = None,
    date: Optional[str] = None,
    start_time: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    limit: int = 20
):
    """
    Search courts with filters and availability check
    
    Args:
        search: Search text (court name, property name, address, city)
        date: Date for availability check (YYYY-MM-DD)
        start_time: Start time for availability check (HH:MM)
        sport_type: Filter by sport type
        min_price: Minimum price per hour
        max_price: Maximum price per hour
        page: Page number
        limit: Items per page
    
    Returns:
        Response with courts list and pagination info
    """
    from shared.repositories import court_repo
    
    # Search courts with filters
    courts, total = court_repo.search_courts_with_filters(
        db,
        search=search,
        sport_type=sport_type,
        min_price=min_price,
        max_price=max_price,
        date_val=date,
        start_time=start_time,
        page=page,
        limit=limit
    )
    
    # Format response
    items = []
    for court in courts:
        # Get base price
        base_price = court_repo.get_base_price(db, court.id)
        
        # Check availability if date and time provided
        is_available = None
        if date and start_time:
            is_available = court_repo.check_court_availability(
                db,
                court.id,
                date,
                start_time
            )
            
            # Skip courts that are not available when filtering by time
            if not is_available:
                continue
        
        # Format court data
        court_data = {
            "id": court.id,
            "name": court.name,
            "sport_types": court.sport_types,
            "description": court.description,
            "specifications": court.specifications,
            "amenities": court.amenities,
            "base_price": base_price,
            "is_indoor": court.specifications.get("is_indoor") if court.specifications else None,
            "surface_type": court.specifications.get("surface_type") if court.specifications else None,
            "property": {
                "id": court.property.id,
                "name": court.property.name,
                "address": court.property.address,
                "city": court.property.city,
                "state": court.property.state,
                "phone": court.property.phone,
                "email": court.property.email,
                "maps_link": court.property.maps_link,
                "amenities": court.property.amenities
            },
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
        
        # Add availability status if checked
        if is_available is not None:
            court_data["is_available"] = is_available
        
        items.append(court_data)
    
    # Recalculate total based on filtered results
    actual_total = len(items) if (date and start_time) else total
    
    # Pagination info
    data = {
        "items": items,
        "total": actual_total,
        "page": page,
        "limit": limit,
        "pages": (actual_total + limit - 1) // limit if actual_total > 0 else 0
    }
    
    return make_response(True, "Courts retrieved successfully", data=data)


