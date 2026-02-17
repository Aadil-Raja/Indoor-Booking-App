from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from app.services import property_service
from shared.schemas.property import PropertyCreate, PropertyUpdate
from shared.models import User

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Create a new property (Owner only)"""
    return property_service.create_property(db, owner_id=current_user.id, data=payload)


@router.get("")
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """List all properties owned by current user"""
    return property_service.get_owner_properties(db, owner_id=current_user.id)


@router.get("/{property_id}")
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Get property details with courts"""
    return property_service.get_property_details(db, property_id=property_id, owner_id=current_user.id)


@router.patch("/{property_id}")
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Update property"""
    return property_service.update_property(db, property_id=property_id, owner_id=current_user.id, data=payload)


@router.delete("/{property_id}")
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_owner)
):
    """Delete property"""
    return property_service.delete_property(db, property_id=property_id, owner_id=current_user.id)
