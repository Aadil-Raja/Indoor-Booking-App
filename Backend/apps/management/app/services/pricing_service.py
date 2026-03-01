from sqlalchemy.orm import Session
from shared.repositories import property_repo, court_repo, pricing_repo
from shared.utils.response_utils import make_response
from shared.utils import OwnerContext
from shared.schemas.pricing import CourtPricingCreate, CourtPricingUpdate


def create_pricing(db: Session, *, court_id: int, current_owner: OwnerContext, data: CourtPricingCreate):
    """Create a new pricing rule for court"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_profile_id != current_owner.owner_profile_id:
        return make_response(False, "Access denied", status_code=403)
    
    if pricing_repo.check_overlap(db, court_id, data.days, data.start_time, data.end_time):
        return make_response(
            False,
            "Pricing rule overlaps with existing rule for same days and time",
            status_code=409
        )
    
    try:
        pricing = pricing_repo.create(
            db,
            court_id=court_id,
            **data.model_dump()
        )
        return make_response(
            True,
            "Pricing rule created successfully",
            data={
                "id": pricing.id,
                "days": pricing.days,
                "start_time": pricing.start_time.isoformat(),
                "end_time": pricing.end_time.isoformat(),
                "price_per_hour": pricing.price_per_hour
            },
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to create pricing rule", status_code=500, error=str(e))


def get_court_pricing(db: Session, *, court_id: int, current_owner: OwnerContext):
    """Get all pricing rules for a court"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_profile_id != current_owner.owner_profile_id:
        return make_response(False, "Access denied", status_code=403)

    
    pricing_rules = pricing_repo.get_by_court(db, court_id)
    
    data = [
        {
            "id": p.id,
            "days": p.days,
            "start_time": p.start_time.isoformat(),
            "end_time": p.end_time.isoformat(),
            "price_per_hour": p.price_per_hour,
            "label": p.label
        }
        for p in pricing_rules
    ]
    
    return make_response(True, "Pricing rules retrieved successfully", data=data)


def update_pricing(db: Session, *, pricing_id: int, current_owner: OwnerContext, data: CourtPricingUpdate):
    """Update pricing rule"""
    pricing = pricing_repo.get_by_id(db, pricing_id)
    
    if not pricing:
        return make_response(False, "Pricing rule not found", status_code=404)
    
    court = court_repo.get_by_id(db, pricing.court_id)
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_profile_id != current_owner.owner_profile_id:
        return make_response(False, "Access denied", status_code=403)
    
    update_data = data.model_dump(exclude_unset=True)
    if any(key in update_data for key in ['days', 'start_time', 'end_time']):
        days = update_data.get('days', pricing.days)
        start_time = update_data.get('start_time', pricing.start_time)
        end_time = update_data.get('end_time', pricing.end_time)
        
        if pricing_repo.check_overlap(db, pricing.court_id, days, start_time, end_time, exclude_id=pricing_id):
            return make_response(
                False,
                "Updated pricing rule would overlap with existing rule",
                status_code=409
            )
    
    try:
        updated = pricing_repo.update(db, pricing, **update_data)
        return make_response(
            True,
            "Pricing rule updated successfully",
            data={"id": updated.id}
        )
    except Exception as e:
        return make_response(False, "Failed to update pricing rule", status_code=500, error=str(e))


def delete_pricing(db: Session, *, pricing_id: int, current_owner: OwnerContext):
    """Delete pricing rule"""
    pricing = pricing_repo.get_by_id(db, pricing_id)
    
    if not pricing:
        return make_response(False, "Pricing rule not found", status_code=404)
    
    court = court_repo.get_by_id(db, pricing.court_id)
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_profile_id != current_owner.owner_profile_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        pricing_repo.delete(db, pricing)
        return make_response(True, "Pricing rule deleted successfully")
    except Exception as e:
        return make_response(False, "Failed to delete pricing rule", status_code=500, error=str(e))
