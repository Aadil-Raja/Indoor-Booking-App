from sqlalchemy.orm import Session
from app.repositories import court_repo, property_repo
from app.utils.response_utils import make_response
from shared.schemas.court import CourtCreate, CourtUpdate


def create_court(db: Session, *, property_id: int, owner_id: int, data: CourtCreate):
    """Create a new court for property"""
    # Verify property exists and belongs to owner
    property = property_repo.get_by_id(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        court = court_repo.create(
            db,
            property_id=property_id,
            **data.model_dump()
        )
        return make_response(
            True,
            "Court created successfully",
            data={"id": court.id, "name": court.name, "sport_type": court.sport_type},
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to create court", status_code=500, error=str(e))


def get_property_courts(db: Session, *, property_id: int, owner_id: int):
    """Get all courts for a property"""
    # Verify property exists and belongs to owner
    property = property_repo.get_by_id(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    courts = court_repo.get_by_property(db, property_id)
    
    data = [
        {
            "id": c.id,
            "name": c.name,
            "sport_type": c.sport_type,
            "description": c.description,
            "specifications": c.specifications,
            "amenities": c.amenities,
            "is_active": c.is_active
        }
        for c in courts
    ]
    
    return make_response(True, "Courts retrieved successfully", data=data)


def get_court_details(db: Session, *, court_id: int, owner_id: int):
    """Get court details"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    # Verify ownership through property
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    data = {
        "id": court.id,
        "property_id": court.property_id,
        "name": court.name,
        "sport_type": court.sport_type,
        "description": court.description,
        "specifications": court.specifications,
        "amenities": court.amenities,
        "is_active": court.is_active,
        "created_at": court.created_at.isoformat() if court.created_at else None
    }
    
    return make_response(True, "Court retrieved successfully", data=data)


def update_court(db: Session, *, court_id: int, owner_id: int, data: CourtUpdate):
    """Update court"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    # Verify ownership through property
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        updated = court_repo.update(db, court, **data.model_dump(exclude_unset=True))
        return make_response(
            True,
            "Court updated successfully",
            data={"id": updated.id, "name": updated.name}
        )
    except Exception as e:
        return make_response(False, "Failed to update court", status_code=500, error=str(e))


def delete_court(db: Session, *, court_id: int, owner_id: int):
    """Delete court"""
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    # Verify ownership through property
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        court_repo.delete(db, court)
        return make_response(True, "Court deleted successfully")
    except Exception as e:
        return make_response(False, "Failed to delete court", status_code=500, error=str(e))
