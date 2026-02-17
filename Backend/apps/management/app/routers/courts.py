from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from app.services import court_service
from shared.schemas.court import CourtCreate, CourtUpdate
from shared.models import User

router = APIRouter(tags=["Courts"])


@router.post("/properties/{property_id}/courts", status_code=status.HTTP_201_CREATED)
def create_court(
    property_id: int,
    payload: CourtCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Create a new court for property (Owner only)"""
    return court_service.create_court(db, property_id=property_id, owner_id=current_user.id, data=payload)


@router.get("/properties/{property_id}/courts")
def list_courts(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """List all courts for a property"""
    return court_service.get_property_courts(db, property_id=property_id, owner_id=current_user.id)


@router.get("/courts/{court_id}")
def get_court(
    court_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Get court details"""
    return court_service.get_court_details(db, court_id=court_id, owner_id=current_user.id)


@router.patch("/courts/{court_id}")
def update_court(
    court_id: int,
    payload: CourtUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Update court"""
    return court_service.update_court(db, court_id=court_id, owner_id=current_user.id, data=payload)


@router.delete("/courts/{court_id}")
def delete_court(
    court_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Delete court"""
    return court_service.delete_court(db, court_id=court_id, owner_id=current_user.id)
