from sqlalchemy.orm import Session
from shared.repositories import booking_repo, property_repo, court_repo, pricing_repo, availability_repo
from shared.utils.response_utils import make_response
from shared.utils import OwnerContext
from shared.schemas.booking import BookingCreate
from shared.models import BookingStatus, PaymentStatus, CourtPricing
from datetime import datetime, timedelta

# Re-export booking_service functions from shared for backward compatibility
from shared.services.booking_service import (
    create_booking,
    get_user_bookings,
    get_booking_details,
    cancel_booking,
    confirm_booking,
    complete_booking,
    get_owner_bookings
)

