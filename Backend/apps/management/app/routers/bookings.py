from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_user, get_current_customer, get_current_owner
from app.services import booking_service
from shared.schemas.booking import BookingCreate
from shared.models import User

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """Create a new booking (Customer only)"""
    return booking_service.create_booking(db, customer_id=current_user.id, data=payload)


@router.get("")
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List bookings for current user
    - Customers see their bookings
    - Owners see bookings for their properties
    """
    if current_user.role.value == "owner":
        return booking_service.get_owner_bookings(db, owner_id=current_user.id)
    else:
        return booking_service.get_user_bookings(db, user_id=current_user.id)


@router.get("/{booking_id}")
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get booking details (Customer or Owner)"""
    return booking_service.get_booking_details(db, booking_id=booking_id, user_id=current_user.id)


@router.patch("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """Cancel booking (Customer only)"""
    return booking_service.cancel_booking(db, booking_id=booking_id, user_id=current_user.id)


@router.patch("/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Confirm booking (Owner only)"""
    return booking_service.confirm_booking(db, booking_id=booking_id, owner_id=current_user.id)


@router.patch("/{booking_id}/complete")
def complete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Mark booking as completed (Owner only)"""
    return booking_service.complete_booking(db, booking_id=booking_id, owner_id=current_user.id)
