from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from shared.services import property_service
from shared.utils import OwnerContext
from shared.schemas.property import PropertyCreate, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Create a new property (Owner only)"""
    return property_service.create_property(db, current_owner=current_owner, data=payload)


@router.get("")
def list_properties(
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """List all properties owned by current user"""
    return property_service.get_owner_properties(db, current_owner=current_owner)


@router.get("/{property_id}")
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Get property details with courts"""
    return property_service.get_property_details(db, property_id=property_id, current_owner=current_owner)


@router.patch("/{property_id}")
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Update property"""
    return property_service.update_property(db, property_id=property_id, current_owner=current_owner, data=payload)


@router.delete("/{property_id}")
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Delete property"""
    return property_service.delete_property(db, property_id=property_id, current_owner=current_owner)
