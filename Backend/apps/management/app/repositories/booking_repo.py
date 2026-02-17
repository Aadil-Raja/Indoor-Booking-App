from sqlalchemy.orm import Session, joinedload
from shared.models import Booking, BookingStatus, PaymentStatus
from typing import Optional, List
from datetime import date, time


def create(
    db: Session,
    *,
    customer_id: int,
    court_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    total_hours: float,
    price_per_hour: float,
    total_price: float,
    notes: Optional[str] = None
) -> Booking:
    """Create a new booking"""
    booking = Booking(
        customer_id=customer_id,
        court_id=court_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        total_hours=total_hours,
        price_per_hour=price_per_hour,
        total_price=total_price,
        notes=notes,
        status=BookingStatus.pending,
        payment_status=PaymentStatus.pending
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    """Get booking by ID"""
    return db.query(Booking).filter(Booking.id == booking_id).first()


def get_with_details(db: Session, booking_id: int) -> Optional[Booking]:
    """Get booking with court and property details"""
    return (
        db.query(Booking)
        .options(
            joinedload(Booking.court).joinedload("property"),
            joinedload(Booking.customer)
        )
        .filter(Booking.id == booking_id)
        .first()
    )


def get_by_customer(db: Session, customer_id: int) -> List[Booking]:
    """Get all bookings for a customer"""
    return (
        db.query(Booking)
        .options(
            joinedload(Booking.court).joinedload("property")
        )
        .filter(Booking.customer_id == customer_id)
        .order_by(Booking.booking_date.desc(), Booking.start_time.desc())
        .all()
    )


def get_by_court(db: Session, court_id: int, from_date: Optional[date] = None) -> List[Booking]:
    """Get all bookings for a court"""
    query = (
        db.query(Booking)
        .options(joinedload(Booking.customer))
        .filter(Booking.court_id == court_id)
    )
    
    if from_date:
        query = query.filter(Booking.booking_date >= from_date)
    
    return query.order_by(Booking.booking_date, Booking.start_time).all()


def get_by_property_owner(db: Session, owner_id: int) -> List[Booking]:
    """Get all bookings for properties owned by user"""
    return (
        db.query(Booking)
        .join(Booking.court)
        .join("property")
        .options(
            joinedload(Booking.court).joinedload("property"),
            joinedload(Booking.customer)
        )
        .filter("property.owner_id" == owner_id)
        .order_by(Booking.booking_date.desc(), Booking.start_time.desc())
        .all()
    )


def check_conflict(
    db: Session,
    court_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    exclude_booking_id: Optional[int] = None
) -> bool:
    """Check if booking conflicts with existing bookings"""
    query = db.query(Booking).filter(
        Booking.court_id == court_id,
        Booking.booking_date == booking_date,
        Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed])
    )
    
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    
    existing = query.all()
    
    for booking in existing:
        # Check if time ranges overlap
        if not (end_time <= booking.start_time or start_time >= booking.end_time):
            return True
    
    return False


def update_status(db: Session, booking: Booking, status: BookingStatus) -> Booking:
    """Update booking status"""
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking


def update_payment_status(db: Session, booking: Booking, payment_status: PaymentStatus) -> Booking:
    """Update payment status"""
    booking.payment_status = payment_status
    db.commit()
    db.refresh(booking)
    return booking
