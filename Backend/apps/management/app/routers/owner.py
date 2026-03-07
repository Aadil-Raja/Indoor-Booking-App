from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from shared.services import owner_service
from shared.utils import OwnerContext
from shared.schemas.owner import OwnerProfileCreate, OwnerProfileUpdate

router = APIRouter(prefix="/owner", tags=["Owner"])


@router.post("/profile", status_code=status.HTTP_200_OK)
def create_or_update_profile(
    payload: OwnerProfileCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Update owner profile (Owner only)"""
    return owner_service.create_or_update_profile(db, current_owner=current_owner, data=payload)


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Get owner profile (Owner only)"""
    return owner_service.get_profile(db, current_owner=current_owner)


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """
    Get dashboard statistics (Owner only)
    
    Returns:
    - Total properties, courts, bookings
    - Booking status breakdown
    - Revenue statistics
    - Revenue by property
    - Recent bookings
    """
    return owner_service.get_dashboard_stats(db, current_owner=current_owner)
