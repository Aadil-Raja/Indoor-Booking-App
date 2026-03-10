"""
Booking service for business logic operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from shared.repositories import booking_repo, court_repo, pricing_repo, availability_repo, property_repo
from shared.utils.response_utils import make_response
from shared.utils import OwnerContext
from shared.schemas.booking import BookingCreate
from shared.models import BookingStatus, PaymentStatus, CourtPricing
from datetime import datetime, timedelta
from typing import Optional


def create_booking(db: Session, *, customer_id: int, data: BookingCreate):
    """Create a new booking"""
    court = court_repo.get_by_id(db, data.court_id)

    if not court or not court.is_active:
        return make_response(False, "Court not found or inactive", status_code=404)

    blocked_slots = availability_repo.get_by_date(db, data.court_id, data.booking_date)
    for block in blocked_slots:
        if not (data.end_time <= block.start_time or data.start_time >= block.end_time):
            return make_response(
                False,
                f"Court is not available during this time. Reason: {block.reason or 'Blocked'}",
                status_code=409
            )

    if booking_repo.check_conflict(db, data.court_id, data.booking_date, data.start_time, data.end_time):
        return make_response(False, "This time slot is already booked", status_code=409)

    day_of_week = data.booking_date.weekday()
     
    # Find pricing rule that covers the booking time slot
    # Get all pricing rules for this day and filter in Python
    pricing_candidates = (
        db.query(CourtPricing)
        .filter(
            CourtPricing.court_id == data.court_id,
            CourtPricing.days.any(day_of_week)
        )
        .all()
    )
    
    print(f"DEBUG: Found {len(pricing_candidates)} pricing candidates for day {day_of_week}")
    
    # Filter pricing rules in Python to find one that covers the booking start time
    pricing = None
    for p in pricing_candidates:
        print(f"DEBUG: Checking pricing {p.id}: {p.start_time} <= {data.start_time} <= {p.end_time}?")
        
        # Check if booking start time falls within pricing range
        if p.start_time <= data.start_time:
            # Check end time - handle XX:59 format
            if p.end_time >= data.start_time:
                print(f"DEBUG: Pricing {p.id} matches!")
                pricing = p
                break
            # Special case: if end_time is XX:59 and booking start is in that hour
            elif p.end_time.minute == 59 and p.end_time.hour >= data.start_time.hour:
                print(f"DEBUG: Pricing {p.id} matches (XX:59 format)!")
                pricing = p
                break

    if not pricing:
        print(f"DEBUG: No pricing found for start_time: {data.start_time}, day: {day_of_week}")
        return make_response(False, "No pricing available for this time slot", status_code=400)
    

    # With XX:00-XX:59 pricing, duration calculation is straightforward
    start_datetime = datetime.combine(data.booking_date, data.start_time)
    end_datetime = datetime.combine(data.booking_date, data.end_time)
    # Handle midnight crossing for bookings (11 PM - 12 AM becomes 11 PM - 12 AM next day)
    if data.end_time <= data.start_time:
        end_datetime = datetime.combine(data.booking_date + timedelta(days=1), data.end_time)
    
    # Calculate total hours
    # Since we use XX:00-XX:59 format, each hour slot is exactly 1 hour
    # For example: 01:00-01:59 is 1 hour, 01:00-02:59 is 2 hours, etc.
    total_seconds = (end_datetime - start_datetime).total_seconds()
    total_hours = total_seconds / 3600
    
    # Round to nearest hour to handle XX:59 format correctly
    # 01:00 to 01:59 = 3599 seconds = 0.9997 hours, should be 1 hour
    # 01:00 to 02:59 = 7199 seconds = 1.9997 hours, should be 2 hours
    total_hours = round(total_hours)
    
    total_price = total_hours * pricing.price_per_hour

    try:
        booking = booking_repo.create(
            db,
            customer_id=customer_id,
            court_id=data.court_id,
            booking_date=data.booking_date,
            start_time=data.start_time,
            end_time=data.end_time,
            total_hours=total_hours,
            price_per_hour=pricing.price_per_hour,
            total_price=total_price,
            notes=data.notes
        )

        return make_response(
            True,
            "Booking created successfully",
            data={
                "id": booking.id,
                "booking_date": booking.booking_date.isoformat(),
                "start_time": booking.start_time.isoformat(),
                "end_time": booking.end_time.isoformat(),
                "total_price": booking.total_price,
                "status": booking.status.value,
                "payment_status": booking.payment_status.value
            },
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to create booking", status_code=500, error=str(e))


def get_user_bookings(db: Session, *, user_id: int, status_filter: Optional[str] = None):
    """Get all bookings for a user"""
    bookings = booking_repo.get_by_customer(db, user_id)

    # Filter by status if provided
    if status_filter:
        bookings = [b for b in bookings if b.status.value == status_filter]

    data = [
        {
            "id": b.id,
            "booking_date": b.booking_date.isoformat(),
            "start_time": b.start_time.isoformat(),
            "end_time": b.end_time.isoformat(),
            "total_price": b.total_price,
            "status": b.status.value,
            "total_hours": b.total_hours,
            "payment_status": b.payment_status.value,
            "court_id": b.court_id,
            "court_name": b.court.name,
            "sport_types": b.court.sport_types,
            "property_name": b.court.property.name,
            "property_address": b.court.property.address
        }
        for b in bookings
    ]

    return make_response(True, "Bookings retrieved successfully", data=data)


def get_booking_details(db: Session, *, booking_id: int, user_id: int):
    """Get booking details"""
    booking = booking_repo.get_with_details(db, booking_id)

    if not booking:
        return make_response(False, "Booking not found", status_code=404)

    is_customer = booking.customer_id == user_id
    is_owner = booking.court.property.owner_profile_id  # We'll check this in the router

    if not is_customer and not is_owner:
        return make_response(False, "Access denied", status_code=403)

    data = {
        "id": booking.id,
        "booking_date": booking.booking_date.isoformat(),
        "start_time": booking.start_time.isoformat(),
        "end_time": booking.end_time.isoformat(),
        "total_hours": booking.total_hours,
        "price_per_hour": booking.price_per_hour,
        "total_price": booking.total_price,
        "status": booking.status.value,
        "payment_status": booking.payment_status.value,
        "notes": booking.notes,
        "court": {
            "id": booking.court.id,
            "name": booking.court.name,
            "sport_types": booking.court.sport_types
        },
        "property": {
            "id": booking.court.property.id,
            "name": booking.court.property.name,
            "address": booking.court.property.address,
            "phone": booking.court.property.phone
        },
        "customer": {
            "id": booking.customer.id,
            "name": booking.customer.Name,
            "email": booking.customer.email
        } if is_owner else None
    }

    return make_response(True, "Booking details retrieved successfully", data=data)


def cancel_booking(db: Session, *, booking_id: int, user_id: int):
    """Cancel a booking (customer only)"""
    booking = booking_repo.get_with_details(db, booking_id)

    if not booking:
        return make_response(False, "Booking not found", status_code=404)

    if booking.customer_id != user_id:
        return make_response(False, "Only the customer can cancel their booking", status_code=403)

    if booking.status == BookingStatus.cancelled:
        return make_response(False, "Booking is already cancelled", status_code=400)

    if booking.status == BookingStatus.completed:
        return make_response(False, "Cannot cancel completed booking", status_code=400)

    try:
        booking_repo.update_status(db, booking, BookingStatus.cancelled)

        if booking.payment_status == PaymentStatus.paid:
            booking_repo.update_payment_status(db, booking, PaymentStatus.refunded)

        return make_response(True, "Booking cancelled successfully")
    except Exception as e:
        return make_response(False, "Failed to cancel booking", status_code=500, error=str(e))


def confirm_booking(db: Session, *, booking_id: int, current_owner: OwnerContext):
    """Confirm a booking (owner only)"""
    booking = booking_repo.get_with_details(db, booking_id)

    if not booking:
        return make_response(False, "Booking not found", status_code=404)

    if booking.court.property.owner_profile_id != current_owner.owner_profile_id:
        return make_response(False, "Only the property owner can confirm bookings", status_code=403)

    if booking.status != BookingStatus.pending:
        return make_response(False, f"Cannot confirm booking with status: {booking.status.value}", status_code=400)

    try:
        booking_repo.update_status(db, booking, BookingStatus.confirmed)
        return make_response(True, "Booking confirmed successfully")
    except Exception as e:
        return make_response(False, "Failed to confirm booking", status_code=500, error=str(e))


def complete_booking(db: Session, *, booking_id: int, current_owner: OwnerContext):
    """Mark booking as completed (owner only)"""
    booking = booking_repo.get_with_details(db, booking_id)

    if not booking:
        return make_response(False, "Booking not found", status_code=404)

    if booking.court.property.owner_profile_id != current_owner.owner_profile_id:
        return make_response(False, "Only the property owner can complete bookings", status_code=403)

    if booking.status not in [BookingStatus.pending, BookingStatus.confirmed]:
        return make_response(False, f"Cannot complete booking with status: {booking.status.value}", status_code=400)

    try:
        booking_repo.update_status(db, booking, BookingStatus.completed)
        return make_response(True, "Booking marked as completed")
    except Exception as e:
        return make_response(False, "Failed to complete booking", status_code=500, error=str(e))


def get_owner_bookings(db: Session, *, current_owner: OwnerContext):
    """Get all bookings for properties owned by user"""
    bookings = booking_repo.get_by_property_owner(db, current_owner.owner_profile_id)

    data = [
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
        for b in bookings
    ]

    return make_response(True, "Bookings retrieved successfully", data=data)
