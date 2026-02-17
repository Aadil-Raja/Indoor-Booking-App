from sqlalchemy.orm import Session
from app.repositories import availability_repo, court_repo, property_repo
from app.utils.response_utils import make_response
from shared.schemas.availability import CourtAvailabilityCreate
from datetime import date


def block_time_slot(db: Session, *, court_id: int, owner_id: int, data: CourtAvailabilityCreate):
    """Block a time slot for a court"""
    # Verify court exists and belongs to owner
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    # Check for overlapping blocks
    if availability_repo.check_overlap(db, court_id, data.date, data.start_time, data.end_time):
        return make_response(
            False,
            "Time slot overlaps with existing blocked slot",
            status_code=409
        )
    
    try:
        availability = availability_repo.create(
            db,
            court_id=court_id,
            date_val=data.date,
            start_time=data.start_time,
            end_time=data.end_time,
            reason=data.reason
        )
        return make_response(
            True,
            "Time slot blocked successfully",
            data={
                "id": availability.id,
                "date": availability.date.isoformat(),
                "start_time": availability.start_time.isoformat(),
                "end_time": availability.end_time.isoformat(),
                "reason": availability.reason
            },
            status_code=201
        )
    except Exception as e:
        return make_response(False, "Failed to block time slot", status_code=500, error=str(e))


def get_blocked_slots(db: Session, *, court_id: int, owner_id: int, from_date: date = None):
    """Get all blocked slots for a court"""
    # Verify court exists and belongs to owner
    court = court_repo.get_by_id(db, court_id)
    
    if not court:
        return make_response(False, "Court not found", status_code=404)
    
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    blocked_slots = availability_repo.get_by_court(db, court_id, from_date or date.today())
    
    data = [
        {
            "id": slot.id,
            "date": slot.date.isoformat(),
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "reason": slot.reason
        }
        for slot in blocked_slots
    ]
    
    return make_response(True, "Blocked slots retrieved successfully", data=data)


def unblock_time_slot(db: Session, *, availability_id: int, owner_id: int):
    """Unblock a time slot"""
    availability = availability_repo.get_by_id(db, availability_id)
    
    if not availability:
        return make_response(False, "Blocked slot not found", status_code=404)
    
    # Verify ownership through court and property
    court = court_repo.get_by_id(db, availability.court_id)
    property = property_repo.get_by_id(db, court.property_id)
    if not property or property.owner_id != owner_id:
        return make_response(False, "Access denied", status_code=403)
    
    try:
        availability_repo.delete(db, availability)
        return make_response(True, "Time slot unblocked successfully")
    except Exception as e:
        return make_response(False, "Failed to unblock time slot", status_code=500, error=str(e))
