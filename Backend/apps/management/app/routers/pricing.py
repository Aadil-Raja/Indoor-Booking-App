from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.deps.auth import get_current_owner
from app.services import pricing_service
from app.utils.shared_utils import OwnerContext
from shared.schemas.pricing import CourtPricingCreate, CourtPricingUpdate

router = APIRouter(tags=["Pricing"])


@router.post("/courts/{court_id}/pricing", status_code=status.HTTP_201_CREATED)
def create_pricing_rule(
    court_id: int,
    payload: CourtPricingCreate,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Create a new pricing rule for court (Owner only)"""
    return pricing_service.create_pricing(db, court_id=court_id, current_owner=current_owner, data=payload)


@router.get("/courts/{court_id}/pricing")
def list_pricing_rules(
    court_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """List all pricing rules for a court"""
    return pricing_service.get_court_pricing(db, court_id=court_id, current_owner=current_owner)


@router.patch("/pricing/{pricing_id}")
def update_pricing_rule(
    pricing_id: int,
    payload: CourtPricingUpdate,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Update pricing rule"""
    return pricing_service.update_pricing(db, pricing_id=pricing_id, current_owner=current_owner, data=payload)


@router.delete("/pricing/{pricing_id}")
def delete_pricing_rule(
    pricing_id: int,
    db: Session = Depends(get_db),
    current_owner: OwnerContext = Depends(get_current_owner)
):
    """Delete pricing rule"""
    return pricing_service.delete_pricing(db, pricing_id=pricing_id, current_owner=current_owner)
