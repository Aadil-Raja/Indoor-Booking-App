from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from app.services import availability_service
from shared.schemas.availability import CourtAvailabilityCreate
from shared.models import User
from datetime import date
from typing import Optional

router = APIRouter(tags=["Availability"])


@router.post("/courts/{court_id}/availability", status_code=status.HTTP_201_CREATED)
def block_time_slot(
    court_id: int,
    payload: CourtAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Block a time slot for court (Owner only)"""
    return availability_service.block_time_slot(db, court_id=court_id, owner_id=current_user.id, data=payload)


@router.get("/courts/{court_id}/availability")
def list_blocked_slots(
    court_id: int,
    from_date: Optional[date] = Query(None, description="Filter from this date onwards"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """List all blocked slots for a court"""
    return availability_service.get_blocked_slots(db, court_id=court_id, owner_id=current_user.id, from_date=from_date)


@router.delete("/availability/{availability_id}")
def unblock_time_slot(
    availability_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Unblock a time slot"""
    return availability_service.unblock_time_slot(db, availability_id=availability_id, owner_id=current_user.id)
