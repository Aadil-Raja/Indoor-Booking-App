from sqlalchemy.orm import Session
from sqlalchemy import func
from app.repositories import owner_repo, property_repo, court_repo, booking_repo
from app.utils.response_utils import make_response
from shared.schemas.owner import OwnerProfileCreate, OwnerProfileUpdate
from shared.models import Booking, BookingStatus, PaymentStatus, Property, Court
from datetime import datetime, timedelta


def create_or_update_profile(db: Session, *, owner_id: int, data: OwnerProfileCreate):
    """Create or update owner profile"""
    profile = owner_repo.get_by_user_id(db, owner_id)
    
    try:
        if profile:
            # Update existing
            updated = owner_repo.update(db, profile, **data.model_dump(exclude_unset=True))
            return make_response(
                True,
                "Profile updated successfully",
                data={
                    "id": updated.id,
                    "business_name": updated.business_name,
                    "phone": updated.phone,
                    "address": updated.address,
                    "verified": updated.verified
                }
            )
        else:
            # Create new
            profile = owner_repo.create(db, user_id=owner_id, **data.model_dump())
            return make_response(
                True,
                "Profile created successfully",
                data={
                    "id": profile.id,
                    "business_name": profile.business_name,
                    "phone": profile.phone,
                    "address": profile.address,
                    "verified": profile.verified
                },
                status_code=201
            )
    except Exception as e:
        return make_response(False, "Failed to save profile", status_code=500, error=str(e))


def get_profile(db: Session, *, owner_id: int):
    """Get owner profile"""
    profile = owner_repo.get_by_user_id(db, owner_id)
    
    if not profile:
        return make_response(False, "Profile not found", status_code=404)
    
    data = {
        "id": profile.id,
        "business_name": profile.business_name,
        "phone": profile.phone,
        "address": profile.address,
        "verified": profile.verified,
        "created_at": profile.created_at.isoformat() if profile.created_at else None
    }
    
    return make_response(True, "Profile retrieved successfully", data=data)


def get_dashboard_stats(db: Session, *, owner_id: int):
    """Get dashboard statistics for owner"""
    # Get properties count
    properties = property_repo.get_by_owner(db, owner_id)
    total_properties = len(properties)
    
    # Get courts count
    total_courts = sum(len(p.courts) for p in properties)
    
    # Get bookings for owner's properties
    bookings = booking_repo.get_by_property_owner(db, owner_id)
    
    # Calculate stats
    total_bookings = len(bookings)
    pending_bookings = sum(1 for b in bookings if b.status == BookingStatus.pending)
    confirmed_bookings = sum(1 for b in bookings if b.status == BookingStatus.confirmed)
    completed_bookings = sum(1 for b in bookings if b.status == BookingStatus.completed)
    cancelled_bookings = sum(1 for b in bookings if b.status == BookingStatus.cancelled)
    
    # Calculate revenue
    total_revenue = sum(b.total_price for b in bookings if b.status == BookingStatus.completed)
    pending_revenue = sum(b.total_price for b in bookings if b.status == BookingStatus.pending)
    confirmed_revenue = sum(b.total_price for b in bookings if b.status == BookingStatus.confirmed)
    
    # Revenue by property
    revenue_by_property = {}
    for booking in bookings:
        if booking.status == BookingStatus.completed:
            prop_id = booking.court.property_id
            prop_name = booking.court.property.name
            
            if prop_id not in revenue_by_property:
                revenue_by_property[prop_id] = {
                    "property_id": prop_id,
                    "property_name": prop_name,
                    "total_bookings": 0,
                    "total_revenue": 0.0
                }
            
            revenue_by_property[prop_id]["total_bookings"] += 1
            revenue_by_property[prop_id]["total_revenue"] += booking.total_price
    
    # Recent bookings (last 10)
    recent_bookings = sorted(bookings, key=lambda b: (b.booking_date, b.start_time), reverse=True)[:10]
    
    data = {
        "stats": {
            "total_properties": total_properties,
            "total_courts": total_courts,
            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "confirmed_bookings": confirmed_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "total_revenue": total_revenue,
            "pending_revenue": pending_revenue,
            "confirmed_revenue": confirmed_revenue
        },
        "revenue_by_property": list(revenue_by_property.values()),
        "recent_bookings": [
            {
                "id": b.id,
                "booking_date": b.booking_date.isoformat(),
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "total_price": b.total_price,
                "status": b.status.value,
                "payment_status": b.payment_status.value,
                "court_name": b.court.name,
                "property_name": b.court.property.name,
                "customer_name": b.customer.Name,
                "customer_email": b.customer.email
            }
            for b in recent_bookings
        ]
    }
    
    return make_response(True, "Dashboard stats retrieved successfully", data=data)
