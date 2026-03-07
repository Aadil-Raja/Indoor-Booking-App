from sqlalchemy.orm import Session
from shared.repositories import property_repo, court_repo, availability_repo
from shared.utils.response_utils import make_response
from shared.utils import OwnerContext
from shared.schemas.availability import CourtAvailabilityCreate
from datetime import date

# Re-export availability_service functions from shared for backward compatibility
from shared.services.availability_service import (
    block_time_slot,
    get_blocked_slots,
    unblock_time_slot
)

