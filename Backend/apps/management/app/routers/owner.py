from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from app.services import owner_service
from shared.schemas.owner import OwnerProfileCreate, OwnerProfileUpdate
from shared.models import User

router = APIRouter(prefix="/owner", tags=["Owner"])


@router.post("/profile", status_code=status.HTTP_200_OK)
def create_or_update_profile(
    payload: OwnerProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Create or update owner profile (Owner only)"""
    return owner_service.create_or_update_profile(db, owner_id=current_user.id, data=payload)


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Get owner profile (Owner only)"""
    return owner_service.get_profile(db, owner_id=current_user.id)


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
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
    return owner_service.get_dashboard_stats(db, owner_id=current_user.id)
