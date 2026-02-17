from sqlalchemy.orm import Session
from app.repositories import booking_repo, court_repo, property_repo, pricing_repo, availability_repo
from app.utils.response_utils import make_response
from shared.schemas.booking import BookingCreate
from shared.models import BookingStatus, PaymentStatus
from datetime import datetime, timedelta


def create_booking(db: Session, *, customer_id: int, data: BookingCreate):
    """Create a new booking"""
    # Verify court exists and is active
    court = court_repo.get_by_id(db, data.court_id)
    
    if not court or not court.is_active:
        return make_response(False, "Court not found or inactive", status_code=404)
    
    # Check if court is available (not blocked)
    blocked_slots = availability_repo.get_by_date(db, data.court_id, data.booking_date)
    for block in blocked_slots:
        if not (data.end_time <= block.start_time or data.start_time >= block.end_time):
            return make_response(
                False,
                f"Court is not available during this time. Reason: {block.reason or 'Blocked'}",
                status_code=409
            )
    
    # Check for booking conflicts
    if booking_repo.check_conflict(db, data.court_id, data.booking_date, data.start_time, data.end_time):
        return make_response(False, "This time slot is already booked", status_code=409)
    
    # Get pricing for this date and time
    day_of_week = data.booking_date.weekday()
    pricing = (
        db.query(pricing_repo.CourtPricing)
        .filter(
            pricing_repo.CourtPricing.court_id == data.court_id,
            pricing_repo.CourtPricing.days.contains([day_of_week]),
            pricing_repo.CourtPricing.start_time <= data.start_time,
            pricing_repo.CourtPricing.end_time >= data.end_time
        )
        .first()
    )
    
    if not pricing:
        return make_response(False, "No pricing available for this time slot", status_code=400)
    
    # Calculate total
    start_datetime = datetime.combine(data.booking_date, data.start_time)
    end_datetime = datetime.combine(data.booking_date, data.end_time)
    total_hours = (end_datetime - start_datetime).total_seconds() / 3600
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


def get_user_bookings(db: Session, *, user_id: int):
    """Get all bookings for a user"""
    bookings = booking_repo.get_by_customer(db, user_id)
    
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
            "sport_type": b.court.sport_type,
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
    
    # Check access (customer or property owner)
    if booking.customer_id != user_id and booking.court.property.owner_id != user_id:
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
            "sport_type": booking.court.sport_type
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
        } if booking.court.property.owner_id == user_id else None
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
        
        # If payment was made, mark for refund
        if booking.payment_status == PaymentStatus.paid:
            booking_repo.update_payment_status(db, booking, PaymentStatus.refunded)
        
        return make_response(True, "Booking cancelled successfully")
    except Exception as e:
        return make_response(False, "Failed to cancel booking", status_code=500, error=str(e))


def confirm_booking(db: Session, *, booking_id: int, owner_id: int):
    """Confirm a booking (owner only)"""
    booking = booking_repo.get_with_details(db, booking_id)
    
    if not booking:
        return make_response(False, "Booking not found", status_code=404)
    
    if booking.court.property.owner_id != owner_id:
        return make_response(False, "Only the property owner can confirm bookings", status_code=403)
    
    if booking.status != BookingStatus.pending:
        return make_response(False, f"Cannot confirm booking with status: {booking.status.value}", status_code=400)
    
    try:
        booking_repo.update_status(db, booking, BookingStatus.confirmed)
        return make_response(True, "Booking confirmed successfully")
    except Exception as e:
        return make_response(False, "Failed to confirm booking", status_code=500, error=str(e))


def complete_booking(db: Session, *, booking_id: int, owner_id: int):
    """Mark booking as completed (owner only)"""
    booking = booking_repo.get_with_details(db, booking_id)
    
    if not booking:
        return make_response(False, "Booking not found", status_code=404)
    
    if booking.court.property.owner_id != owner_id:
        return make_response(False, "Only the property owner can complete bookings", status_code=403)
    
    if booking.status not in [BookingStatus.pending, BookingStatus.confirmed]:
        return make_response(False, f"Cannot complete booking with status: {booking.status.value}", status_code=400)
    
    try:
        booking_repo.update_status(db, booking, BookingStatus.completed)
        return make_response(True, "Booking marked as completed")
    except Exception as e:
        return make_response(False, "Failed to complete booking", status_code=500, error=str(e))


def get_owner_bookings(db: Session, *, owner_id: int):
    """Get all bookings for properties owned by user"""
    bookings = booking_repo.get_by_property_owner(db, owner_id)
    
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
