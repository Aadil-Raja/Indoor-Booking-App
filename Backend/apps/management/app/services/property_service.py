from sqlalchemy.orm import Session
from app.repositories import property_repo
from app.utils.response_utils import make_response
from shared.schemas.property import PropertyCreate, PropertyUpdate


def create_property(db: Session, *, owner_id: int, data: PropertyCreate):
    """Create a new property for owner"""
    try:
        property = property_repo.create(
            db,
            owner_id=owner_id,
            **data.model_dump()
        )
        return make_response(
            True,
            "Property created successfully",
            data={"id": property.id, "name": property.name},
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to create property", status_code=500, error=str(e))


def get_owner_properties(db: Session, *, owner_id: int):
    """Get all properties owned by user"""
    properties = property_repo.get_by_owner(db, owner_id)
    
    data = [
        {
            "id": p.id,
            "name": p.name,
            "city": p.city,
            "state": p.state,
            "is_active": p.is_active
        }
        for p in properties
    ]
    
    return make_response(
        True,
        "Properties retrieved successfully",
        data=data
    )


def get_property_details(db: Session, *, property_id: int, owner_id: int):
    """Get property with courts"""
    property = property_repo.get_with_courts(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    # Check ownership
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    # Format response
    data = {
        "id": property.id,
        "name": property.name,
        "description": property.description,
        "address": property.address,
        "city": property.city,
        "state": property.state,
        "country": property.country,
        "maps_link": property.maps_link,
        "phone": property.phone,
        "email": property.email,
        "amenities": property.amenities,
        "is_active": property.is_active,
        "created_at": property.created_at.isoformat() if property.created_at else None,
        "courts": [
            {
                "id": c.id,
                "name": c.name,
                "sport_type": c.sport_type,
                "is_active": c.is_active
            }
            for c in property.courts
        ]
    }
    
    return make_response(True, "Property retrieved successfully", data=data)


def update_property(db: Session, *, property_id: int, owner_id: int, data: PropertyUpdate):
    """Update property"""
    property = property_repo.get_by_id(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        updated = property_repo.update(db, property, **data.model_dump(exclude_unset=True))
        return make_response(
            True,
            "Property updated successfully",
            data={"id": updated.id, "name": updated.name}
        )
    except Exception as e:
        return make_response(False, "Failed to update property", status_code=500, error=str(e))


def delete_property(db: Session, *, property_id: int, owner_id: int):
    """Delete property"""
    property = property_repo.get_by_id(db, property_id)
    
    if not property:
        return make_response(False, "Property not found", status_code=404)
    
    if property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        property_repo.delete(db, property)
        return make_response(True, "Property deleted successfully")
    except Exception as e:
        return make_response(False, "Failed to delete property", status_code=500, error=str(e))
